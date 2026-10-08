# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial tests for multi-platform trends engine in backend.agents.trends.
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.trends import (
    MAX_PLATFORMS_PER_TRENDS,
    TrendsAgent,
    compute_virality_score,
)
from backend.database import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    asyncio.run(init_db())


@pytest.fixture()
def bus(monkeypatch):
    sent: list[dict] = []
    warnings: list[dict] = []

    async def fake_send(msg, user_id="local"):
        sent.append(msg)

    async def fake_progress(*a, **k):
        return None

    async def fake_warn(constraint, message, severity="warning",
                        wizard_id=None, user_id="local"):
        warnings.append({"constraint": constraint, "message": message})

    from backend.core.ws_manager import ws_manager
    monkeypatch.setattr(ws_manager, "send", fake_send)
    monkeypatch.setattr(ws_manager, "send_progress", fake_progress)
    monkeypatch.setattr(ws_manager, "send_constraint_warning", fake_warn)
    return {"sent": sent, "warnings": warnings}


@pytest.fixture()
def platforms(monkeypatch):
    calls: list[tuple[str, str]] = []
    outcomes: dict = {}

    async def fake_platform(self, platform, niche, user_settings, user_id="local"):
        calls.append((platform, niche))
        out = outcomes.get(platform, [])
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(TrendsAgent, "_fetch_platform_trends", fake_platform)

    async def no_refine(*a, **k):
        return None
    monkeypatch.setattr("backend.core.ai_retry.ai_refine_search", no_refine)

    async def no_enrich(self, *a, **k):
        return None
    monkeypatch.setattr(TrendsAgent, "_enrich_outlier_metrics", no_enrich)

    return {"calls": calls, "outcomes": outcomes}


@pytest.fixture()
def no_ai_fallback(monkeypatch):
    async def none(self, *a, **k):
        return []
    monkeypatch.setattr(TrendsAgent, "_ai_search_fallback", none)


def _result(video_id="v1", platform="youtube", views=1000, likes=100, **kw):
    return {
        "platform": platform, "video_id": video_id,
        "video_url": f"https://example.com/{video_id}",
        "title": f"Video {video_id}", "author": "@creator",
        "views": views, "likes": likes, "comments": 10, "shares": 5,
        "duration_seconds": 30, **kw,
    }


async def _job() -> str:
    from backend.agents.job_helper import create_job
    return (await create_job("trends", "local", {})).id


def _run(niche="cooking", plats=("youtube",)):
    async def go():
        jid = await _job()
        await TrendsAgent().run(jid, niche, list(plats))
        return jid
    return asyncio.run(go())


async def _saved_count(niche: str) -> int:
    from sqlalchemy import func, select
    from backend.database import AsyncSessionLocal
    from backend.models.trends_result import TrendsResult
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(func.count(TrendsResult.id))
                                 .where(TrendsResult.niche == niche))).scalar_one()


class TestPlatformListHygiene:
    def test_duplicates_are_collapsed(self, bus, platforms):
        _run(plats=["youtube", "YouTube", "youtube "])
        assert [c[0] for c in platforms["calls"]] == ["youtube"]

    def test_the_list_is_capped(self, bus, platforms):
        _run(plats=[f"platform{i}" for i in range(40)])
        assert len(platforms["calls"]) == MAX_PLATFORMS_PER_TRENDS

    def test_an_empty_list_falls_back_to_youtube(self, bus, platforms):
        _run(plats=[])
        assert [c[0] for c in platforms["calls"]] == ["youtube"]

    def test_blank_entries_are_dropped(self, bus, platforms):
        _run(plats=["", "  ", "youtube"])
        assert [c[0] for c in platforms["calls"]] == ["youtube"]

    def test_many_unsupported_platforms_produce_one_aggregated_notice(self, bus, platforms):
        _run(plats=["vimeo", "dailymotion", "rumble", "odysee"])
        aggregated = [w for w in bus["warnings"]
                      if w["constraint"] == "multi_platform_fallback"]
        assert len(aggregated) == 1


class TestPartialFailure:
    def test_a_raising_platform_does_not_stop_the_others(self, bus, platforms, no_ai_fallback):
        platforms["outcomes"]["tiktok"] = RuntimeError("tiktok API down")
        platforms["outcomes"]["youtube"] = [_result("y1")]
        _run(niche="partial-fail", plats=["tiktok", "youtube"])
        assert asyncio.run(_saved_count("partial-fail")) == 1

    def test_the_failure_is_reported_not_swallowed(self, bus, platforms, no_ai_fallback):
        platforms["outcomes"]["tiktok"] = RuntimeError("tiktok API down")
        _run(niche="reported", plats=["tiktok"])
        assert any("tiktok" in w["constraint"] for w in bus["warnings"])

    def test_the_ai_fallback_can_rescue_a_failed_platform(self, bus, platforms, monkeypatch):
        platforms["outcomes"]["tiktok"] = RuntimeError("library exploded")

        async def rescue(self, platform, niche, user_settings):
            return [_result("rescued", platform="tiktok")]
        monkeypatch.setattr(TrendsAgent, "_ai_search_fallback", rescue)
        _run(niche="rescued-niche", plats=["tiktok"])
        assert asyncio.run(_saved_count("rescued-niche")) == 1

    def test_every_platform_failing_still_completes_the_job(self, bus, platforms, no_ai_fallback):
        platforms["outcomes"]["youtube"] = RuntimeError("nope")
        jid = _run(niche="all-fail", plats=["youtube"])

        async def status():
            from sqlalchemy import select
            from backend.database import AsyncSessionLocal
            from backend.models.job import Job
            async with AsyncSessionLocal() as db:
                return (await db.execute(
                    select(Job.status).where(Job.id == jid))).scalar_one()
        assert asyncio.run(status()) in ("success", "failed")

    def test_enrichment_failing_never_costs_the_results(self, bus, platforms, monkeypatch):
        platforms["outcomes"]["youtube"] = [_result("keep-me")]

        async def boom(self, *a, **k):
            raise RuntimeError("outlier enrichment blew up")
        monkeypatch.setattr(TrendsAgent, "_enrich_outlier_metrics", boom)

        _run(niche="enrich-fail", plats=["youtube"])
        assert asyncio.run(_saved_count("enrich-fail")) == 1


class TestEmptyResultRetry:
    def test_an_empty_platform_triggers_one_refined_retry(self, bus, platforms, monkeypatch):
        platforms["outcomes"]["youtube"] = []
        seen = {}

        async def refine(platform, niche, user_settings):
            seen["asked"] = (platform, niche)
            return "cooking recipes"
        monkeypatch.setattr("backend.core.ai_retry.ai_refine_search", refine)

        _run(niche="cooking", plats=["youtube"])
        assert seen["asked"] == ("youtube", "cooking")
        assert [c[1] for c in platforms["calls"]] == ["cooking", "cooking recipes"]

    def test_no_refinement_means_no_retry(self, bus, platforms):
        platforms["outcomes"]["youtube"] = []
        _run(plats=["youtube"])
        assert len(platforms["calls"]) == 1

    def test_a_refinement_failure_is_non_fatal(self, bus, platforms, monkeypatch):
        platforms["outcomes"]["youtube"] = []

        async def boom(*a, **k):
            raise RuntimeError("refiner down")
        monkeypatch.setattr("backend.core.ai_retry.ai_refine_search", boom)
        _run(plats=["youtube"])

    def test_a_platform_with_results_is_not_retried(self, bus, platforms, monkeypatch):
        platforms["outcomes"]["youtube"] = [_result()]

        async def refine(*a, **k):
            raise AssertionError("must not refine a search that worked")
        monkeypatch.setattr("backend.core.ai_retry.ai_refine_search", refine)
        _run(plats=["youtube"])


class TestScoringAndSave:
    def test_results_are_scored_and_saved(self, bus, platforms):
        platforms["outcomes"]["youtube"] = [
            _result("a", views=1_000_000, likes=100_000),
            _result("b", views=10, likes=0),
        ]
        _run(niche="scored", plats=["youtube"])
        assert asyncio.run(_saved_count("scored")) == 2

    def test_a_duplicate_video_is_not_saved_twice(self, bus, platforms):
        platforms["outcomes"]["youtube"] = [_result("dupe"), _result("dupe")]
        _run(niche="dupes", plats=["youtube"])
        assert asyncio.run(_saved_count("dupes")) <= 1

    def test_the_job_reports_completion(self, bus, platforms):
        platforms["outcomes"]["youtube"] = [_result()]
        jid = _run(niche="completes", plats=["youtube"])

        async def row():
            from sqlalchemy import select
            from backend.database import AsyncSessionLocal
            from backend.models.job import Job
            async with AsyncSessionLocal() as db:
                return (await db.execute(
                    select(Job).where(Job.id == jid))).scalar_one()
        assert asyncio.run(row()).status == "success"


class TestResolveVideoUrl:
    def test_youtube(self):
        assert TrendsAgent._resolve_video_url("youtube", "abc", {}) == \
            "https://youtube.com/watch?v=abc"

    def test_tiktok_with_a_handle(self):
        url = TrendsAgent._resolve_video_url(
            "tiktok", "123", {"author": {"unique_id": "someone"}})
        assert url == "https://www.tiktok.com/@someone/video/123"

    def test_tiktok_without_a_handle_still_resolves(self):
        assert TrendsAgent._resolve_video_url("tiktok", "123", {}) == \
            "https://www.tiktok.com/video/123"

    def test_douyin(self):
        assert TrendsAgent._resolve_video_url("douyin", "9", {}) == \
            "https://www.douyin.com/video/9"

    def test_an_unknown_platform_yields_no_url(self):
        assert TrendsAgent._resolve_video_url("myspace", "9", {}) == ""


class TestViralityScore:
    def test_it_stays_inside_zero_to_one_hundred(self):
        for v in (_result(views=0, likes=0),
                  _result(views=10**9, likes=10**8),
                  _result(views=1, likes=10**6)):
            assert 0 <= compute_virality_score(v) <= 100

    def test_engagement_beats_raw_views(self):
        engaged = _result(views=10_000, likes=5_000, comments=2_000)
        flat = _result(views=10_000, likes=5, comments=0)
        assert compute_virality_score(engaged) > compute_virality_score(flat)

    def test_a_zero_view_video_does_not_divide_by_zero(self):
        assert compute_virality_score(_result(views=0, likes=0)) >= 0

    def test_missing_fields_are_survivable(self):
        assert compute_virality_score({"platform": "youtube"}) >= 0


class TestViralityScoreShape:
    def test_a_brand_new_video_outranks_an_identical_old_one(self):
        fresh = _result(views=10_000, likes=1_000,
                        upload_date=datetime.utcnow())
        old = _result(views=10_000, likes=1_000,
                      upload_date=datetime.utcnow() - timedelta(days=900))
        assert compute_virality_score(fresh) >= compute_virality_score(old)

    def test_a_string_metric_does_not_crash_the_scorer(self):
        assert compute_virality_score(
            {"platform": "tiktok", "views": "1000", "likes": "10"}) >= 0

    @pytest.mark.parametrize("junk", [
        {"views": "1.2M", "likes": "many"},
        {"views": None, "likes": None},
        {"views": [], "likes": {}},
        {"views": float("inf"), "likes": float("nan")},
        {"views": 1000, "channel_avg_views": "800"},
        {"views": 1000, "subscriber_count": "50000"},
        {"views": 1000, "subscriber_count": []},
    ])
    def test_no_shape_of_junk_metric_raises(self, junk):
        assert compute_virality_score({"platform": "tiktok", **junk}) >= 0

    def test_the_side_data_it_writes_back_is_still_numeric(self):
        row = {"platform": "youtube", "views": "12000", "likes": "450",
               "subscriber_count": "50000"}
        compute_virality_score(row)
        assert isinstance(row["views_per_hour"], float)
        assert isinstance(row["outlier_score"], float)

    def test_a_row_with_string_metrics_still_saves_alongside_the_others(self, bus, platforms):
        platforms["outcomes"]["youtube"] = [
            _result("good"),
            _result("stringy", views="12000", likes="450"),
        ]
        _run(niche="string-metrics", plats=["youtube"])
        assert asyncio.run(_saved_count("string-metrics")) == 2

    def test_a_missing_author_block_is_survivable(self):
        assert TrendsAgent._resolve_video_url("tiktok", "1", {"author": {}}) == "https://www.tiktok.com/video/1"
        assert TrendsAgent._resolve_video_url("tiktok", "1", {"author": None}) == "https://www.tiktok.com/video/1"

    def test_an_empty_video_id_still_returns_a_string(self):
        for p in ("youtube", "tiktok", "douyin", "other"):
            assert isinstance(TrendsAgent._resolve_video_url(p, "", {}), str)

