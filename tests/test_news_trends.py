# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial tests for backend.agents.news_trends.NewsTrendsAgent.
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    return asyncio.run(coro)


def _article(url, title="Headline", **overrides):
    base = {
        "url": url,
        "title": title,
        "source": "Example News",
        "source_domain": "example.com",
        "engagement": 100,
        "image_url": None,
        "published_at": datetime(2026, 7, 1),
        "virality_score": 42,
    }
    base.update(overrides)
    return base


def _make_session(scalar_queue):
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def execute(stmt):
        result = MagicMock()
        val = scalar_queue.pop(0) if scalar_queue else None
        result.scalar_one_or_none = MagicMock(return_value=val)
        return result

    session.execute = execute

    @asynccontextmanager
    async def factory():
        yield session

    return factory, session


@pytest.fixture
def infra():
    with patch("backend.agents.news_trends.ws_manager.send", new=AsyncMock()) as send_ws, \
         patch("backend.agents.news_trends.ws_manager.send_constraint_warning",
               new=AsyncMock()) as warn, \
         patch("backend.agents.news_trends.update_job_status", new=AsyncMock()) as ujs, \
         patch("backend.agents.news_trends.asyncio.sleep", new=AsyncMock()):
        yield {"send": send_ws, "warn": warn, "ujs": ujs}


def _final_status_calls(ujs):
    out = []
    for c in ujs.await_args_list:
        if len(c.args) >= 2:
            out.append(c.args[1])
        elif "status" in c.kwargs:
            out.append(c.kwargs["status"])
    return out


def _ws_types(send_ws):
    return [
        c.args[0].get("type")
        for c in send_ws.await_args_list
        if c.args and isinstance(c.args[0], dict)
    ]


class TestMultiSourceFlow:
    def test_aggregates_fetches_analyzes_and_stores(self, infra):
        from backend.agents.news_trends import NewsTrendsAgent
        factory, session = _make_session([])

        arts = [_article("https://example.com/a"), _article("https://example.com/b")]
        analyzed = [
            _article("https://example.com/a", full_text="body a",
                     word_count=200, analysis={"angle": "x"}),
            _article("https://example.com/b", full_text="body b",
                     word_count=180, analysis={"angle": "y"}),
        ]

        with patch("backend.agents.news_trends.AsyncSessionLocal",
                   side_effect=lambda: factory()), \
             patch("backend.services.news_scraper.scrape_news",
                   new=AsyncMock(return_value=arts)), \
             patch("backend.services.news_scraper.fetch_article_text",
                   new=AsyncMock(return_value={"text": "full body", "word_count": 200})), \
             patch("backend.services.news_analyzer_service.analyze_articles",
                   new=AsyncMock(return_value=analyzed)):
            _run(NewsTrendsAgent().run(
                job_id="job-1", query="ai regulation",
                expanded_queries=["eu ai act", "openai rule"],
            ))

        assert session.add.call_count == 2
        statuses = _final_status_calls(infra["ujs"])
        assert statuses[-1] == "success"
        types = _ws_types(infra["send"])
        assert "news_results" in types
        assert "job_complete" in types

    def test_empty_sources_warns_and_succeeds_with_zero(self, infra):
        from backend.agents.news_trends import NewsTrendsAgent
        factory, session = _make_session([])

        with patch("backend.agents.news_trends.AsyncSessionLocal",
                   side_effect=lambda: factory()), \
             patch("backend.services.news_scraper.scrape_news",
                   new=AsyncMock(return_value=[])):
            _run(NewsTrendsAgent().run(job_id="job-2", query="empty query"))

        infra["warn"].assert_awaited_once()
        assert infra["warn"].await_args.kwargs["constraint"] == "news_sources_empty"
        assert _final_status_calls(infra["ujs"])[-1] == "success"
        assert session.add.call_count == 0

    def test_ai_analysis_failure_routes_to_job_failed(self, infra):
        from backend.agents.news_trends import NewsTrendsAgent
        factory, session = _make_session([])
        arts = [_article("https://example.com/a")]

        with patch("backend.agents.news_trends.AsyncSessionLocal",
                   side_effect=lambda: factory()), \
             patch("backend.services.news_scraper.scrape_news",
                   new=AsyncMock(return_value=arts)), \
             patch("backend.services.news_scraper.fetch_article_text",
                   new=AsyncMock(return_value={"text": "body", "word_count": 50})), \
             patch("backend.services.news_analyzer_service.analyze_articles",
                   new=AsyncMock(side_effect=RuntimeError("AI rate limit exceeded"))):
            _run(NewsTrendsAgent().run(job_id="job-3", query="fail me"))

        assert _final_status_calls(infra["ujs"])[-1] == "failed"
        assert "job_failed" in _ws_types(infra["send"])
        assert session.add.call_count == 0


class TestDirectUrlFlow:
    def test_direct_url_success(self, infra):
        from backend.agents.news_trends import NewsTrendsAgent
        factory, session = _make_session([])
        article_data = _article("https://example.com/article", full_text="Valid long article body")
        analyzed_article = dict(article_data, analysis={"angle": "exclusive"})

        with patch("backend.agents.news_trends.AsyncSessionLocal",
                   side_effect=lambda: factory()), \
             patch("backend.services.news_scraper.fetch_direct_url",
                   new=AsyncMock(return_value=article_data)), \
             patch("backend.services.news_analyzer_service.analyze_single_article",
                   new=AsyncMock(return_value=analyzed_article)):
            _run(NewsTrendsAgent().run(job_id="job-4", query="", direct_url="https://example.com/article"))

        assert session.add.call_count == 1
        assert _final_status_calls(infra["ujs"])[-1] == "success"
        assert "news_results" in _ws_types(infra["send"])

    def test_direct_url_fails_when_unextractable(self, infra):
        from backend.agents.news_trends import NewsTrendsAgent
        factory, session = _make_session([])
        empty_article = {"url": "https://example.com/paywall", "full_text": None}

        with patch("backend.agents.news_trends.AsyncSessionLocal",
                   side_effect=lambda: factory()), \
             patch("backend.services.news_scraper.fetch_direct_url",
                   new=AsyncMock(return_value=empty_article)), \
             patch.object(NewsTrendsAgent, "_ai_extract_text", new=AsyncMock(return_value=None)):
            _run(NewsTrendsAgent().run(job_id="job-5", query="", direct_url="https://example.com/paywall"))

        assert _final_status_calls(infra["ujs"])[-1] == "failed"
        assert "job_failed" in _ws_types(infra["send"])
        assert session.add.call_count == 0
