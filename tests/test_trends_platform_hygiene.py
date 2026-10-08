# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial tests for platform hygiene and outlier error tolerance in backend.agents.trends.
from unittest.mock import AsyncMock, patch
import pytest

from backend.agents.trends import MAX_PLATFORMS_PER_TRENDS, TrendsAgent


class _FakeDB:
    async def execute(self, *a, **kw):
        class _R:
            def scalar_one_or_none(self):
                return None
        return _R()


class _FakeSessionCM:
    async def __aenter__(self):
        return _FakeDB()

    async def __aexit__(self, *a):
        return False


@pytest.mark.asyncio
async def test_trends_run_caps_platform_list_and_aggregates_warning():
    agent = TrendsAgent()
    queried = []
    warnings = []

    async def fake_platform(platform, niche, user_settings=None, user_id="local"):
        queried.append(platform)
        return []

    many = ["youtube"] + [f"fake{i}" for i in range(20)]
    with patch.object(agent, "_fetch_platform_trends", side_effect=fake_platform), \
         patch.object(agent, "_enrich_outlier_metrics", new=AsyncMock()), \
         patch("backend.agents.trends.ws_manager") as wsm, \
         patch("backend.agents.trends.update_job_status", new=AsyncMock()), \
         patch("backend.agents.trends.AsyncSessionLocal", return_value=_FakeSessionCM()), \
         patch("backend.core.ai_retry.ai_refine_search", new=AsyncMock(return_value=None)), \
         patch.object(agent, "_save_trends", new=AsyncMock(return_value=([], 0)), create=True):
        wsm.send_progress = AsyncMock()
        wsm.send_constraint_warning = AsyncMock(
            side_effect=lambda **kw: warnings.append(kw.get("constraint")))
        wsm.send = AsyncMock()
        try:
            await agent.run(job_id="job-x", niche="cats", platforms=many)
        except Exception:
            pass

    assert len(queried) <= MAX_PLATFORMS_PER_TRENDS
    assert warnings.count("multi_platform_fallback") == 1
    assert not any(w and w.endswith("_no_native_search") for w in warnings)


@pytest.mark.asyncio
async def test_enrich_survives_none_author_url():
    agent = TrendsAgent()
    results = [
        {"platform": "youtube", "author_url": None, "views": 10},
        {"platform": "youtube", "author_url": "https://youtube.com/channel/UCabc123", "views": 5},
    ]
    with patch("backend.core.api_keys.get_youtube_api_key", return_value="fake-key"), \
         patch("backend.services.outlier_detection_service.batch_get_channel_baselines",
               new=AsyncMock(return_value={})), \
         patch("backend.services.outlier_detection_service.enrich_trend_results_with_outliers",
               return_value=None):
        await agent._enrich_outlier_metrics(results, ["youtube"], None)
