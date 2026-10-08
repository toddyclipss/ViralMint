# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial tests for trends save and dedup contract in backend.agents.trends.
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.agents.trends import TrendsAgent


def _fake_trend_item(video_id: str, platform: str, **overrides) -> dict:
    base = {
        "video_id": video_id,
        "platform": platform,
        "video_url": f"https://example.com/{video_id}",
        "title": f"Title {video_id}",
        "author": "Test Author",
        "views": 1000,
        "likes": 50,
        "comments": 5,
        "virality_score": 7.5,
    }
    base.update(overrides)
    return base


def _make_fake_session(existing_keys_to_ids: dict[tuple[str, str], str]):
    fetched_rows = [
        (id_, video_id, platform)
        for (video_id, platform), id_ in existing_keys_to_ids.items()
    ]

    fetched_result = MagicMock()
    fetched_result.fetchall = MagicMock(return_value=fetched_rows)

    next_id = [1000]

    def _fake_flush_side_effect():
        if fake_session._pending_row is not None:
            fake_session._pending_row.id = f"new-{next_id[0]}"
            next_id[0] += 1
            fake_session._pending_row = None

    def _fake_add(row):
        fake_session._pending_row = row

    fake_session = MagicMock()
    fake_session._pending_row = None
    fake_session.execute = AsyncMock(return_value=fetched_result)
    fake_session.add = MagicMock(side_effect=_fake_add)
    fake_session.flush = AsyncMock(side_effect=_fake_flush_side_effect)
    fake_session.commit = AsyncMock()

    class FakeCM:
        async def __aenter__(self):
            return fake_session

        async def __aexit__(self, *a):
            return False

    return FakeCM, fake_session


class TestSaveTrendsDedupDisplay:
    @pytest.mark.asyncio
    async def test_all_new_results_returned_with_fresh_ids(self):
        cm, _session = _make_fake_session(existing_keys_to_ids={})
        with patch("backend.agents.trends.AsyncSessionLocal", return_value=cm()):
            results = [
                _fake_trend_item("a1", "youtube"),
                _fake_trend_item("b2", "youtube"),
                _fake_trend_item("c3", "tiktok"),
            ]
            display, new_count = await TrendsAgent()._save_trends(
                results, job_id="job-1", niche="ai tools", user_id="local",
            )

        assert len(display) == 3
        assert new_count == 3
        for d in display:
            assert d["id"].startswith("new-")

    @pytest.mark.asyncio
    async def test_all_duplicates_still_returned_with_existing_ids(self):
        existing = {
            ("a1", "youtube"): "id-aaa",
            ("b2", "youtube"): "id-bbb",
            ("c3", "tiktok"): "id-ccc",
        }
        cm, session = _make_fake_session(existing_keys_to_ids=existing)
        with patch("backend.agents.trends.AsyncSessionLocal", return_value=cm()):
            results = [
                _fake_trend_item("a1", "youtube"),
                _fake_trend_item("b2", "youtube"),
                _fake_trend_item("c3", "tiktok"),
            ]
            display, new_count = await TrendsAgent()._save_trends(
                results, job_id="job-2", niche="ai tools", user_id="local",
            )

        assert len(display) == 3
        assert new_count == 0
        assert display[0]["id"] == "id-aaa"
        assert display[1]["id"] == "id-bbb"
        assert display[2]["id"] == "id-ccc"
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_new_and_duplicates(self):
        existing = {
            ("a1", "youtube"): "id-aaa",
            ("b2", "youtube"): "id-bbb",
        }
        cm, session = _make_fake_session(existing_keys_to_ids=existing)
        with patch("backend.agents.trends.AsyncSessionLocal", return_value=cm()):
            results = [
                _fake_trend_item("a1", "youtube"),
                _fake_trend_item("brand-new", "youtube"),
                _fake_trend_item("b2", "youtube"),
                _fake_trend_item("c3", "tiktok"),
            ]
            display, new_count = await TrendsAgent()._save_trends(
                results, job_id="job-3", niche="ai tools", user_id="local",
            )

        assert len(display) == 4
        assert new_count == 2
        assert display[0]["id"] == "id-aaa"
        assert display[1]["id"].startswith("new-")
        assert display[2]["id"] == "id-bbb"
        assert display[3]["id"].startswith("new-")
        assert session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_fresh_stats_used_for_duplicates(self):
        existing = {("a1", "youtube"): "id-aaa"}
        cm, _session = _make_fake_session(existing_keys_to_ids=existing)
        with patch("backend.agents.trends.AsyncSessionLocal", return_value=cm()):
            results = [
                _fake_trend_item(
                    "a1", "youtube",
                    views=999999, likes=50000, comments=2000,
                    virality_score=9.5,
                ),
            ]
            display, _ = await TrendsAgent()._save_trends(
                results, job_id="job-4", niche="ai tools", user_id="local",
            )

        assert display[0]["id"] == "id-aaa"
        assert display[0]["views"] == 999999
        assert display[0]["likes"] == 50000
        assert display[0]["comments"] == 2000
        assert display[0]["virality_score"] == 9.5

    @pytest.mark.asyncio
    async def test_empty_input_yields_empty_display(self):
        cm, _session = _make_fake_session(existing_keys_to_ids={})
        with patch("backend.agents.trends.AsyncSessionLocal", return_value=cm()):
            display, new_count = await TrendsAgent()._save_trends(
                [], job_id="job-6", niche="x", user_id="local",
            )
        assert display == []
        assert new_count == 0

    @pytest.mark.asyncio
    async def test_requested_platform_preserved_for_duplicates(self):
        existing = {("a1", "youtube"): "id-aaa"}
        cm, _session = _make_fake_session(existing_keys_to_ids=existing)
        with patch("backend.agents.trends.AsyncSessionLocal", return_value=cm()):
            results = [
                _fake_trend_item("a1", "youtube", requested_platform="bilibili"),
            ]
            display, _ = await TrendsAgent()._save_trends(
                results, job_id="job-7", niche="ai tools", user_id="local",
            )

        assert display[0]["requested_platform"] == "bilibili"
        assert display[0]["platform"] == "youtube"

