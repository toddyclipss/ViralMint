# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial news trends intelligence agent — research, extraction & viral potential analysis.
import asyncio
import hashlib
import json
import logging
from typing import Optional

from sqlalchemy import select

from backend.agents.job_helper import update_job_status
from backend.core.ws_manager import ws_manager
from backend.database import AsyncSessionLocal
from backend.models.trends_result import TrendsResult
from backend.models.user_settings import UserSettings

logger = logging.getLogger(__name__)

MAX_FULL_TEXT_FETCH = 10
TEXT_FETCH_SEMAPHORE = 5


class NewsTrendsAgent:
    """
    Intelligent news trends discovery and parsing engine.
    Scrapes, deduplicates, extracts full text, runs AI analysis, and saves to trends.
    """
    async def run(
        self,
        job_id: str,
        query: str,
        expanded_queries: list[str] | None = None,
        sources: list[str] | None = None,
        direct_url: str | None = None,
        user_id: str = "local",
    ):
        from backend.services.news_scraper import fetch_article_text, fetch_direct_url, scrape_news
        from backend.services.news_analyzer_service import analyze_articles, analyze_single_article

        await update_job_status(job_id, "running", progress_pct=0, current_step="Starting news research...")

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()

        try:
            # ── Direct URL mode ──────────────────────────────────────────
            if direct_url:
                await update_job_status(job_id, "running", progress_pct=20, current_step="Fetching article...")
                article = await fetch_direct_url(direct_url)

                if not article.get("full_text"):
                    await update_job_status(
                        job_id, "running", progress_pct=35,
                        current_step="Standard extraction failed, trying AI extraction...",
                    )
                    ai_text = await self._ai_extract_text(direct_url, user_settings)
                    if ai_text:
                        article["full_text"] = ai_text
                        article["word_count"] = len(ai_text.split())
                        logger.info("AI extraction succeeded for %s (%d words)", direct_url[:60], article["word_count"])

                if not article.get("full_text"):
                    await update_job_status(
                        job_id, "failed",
                        error_message="Could not extract text from that URL. It may be paywalled or blocked.",
                    )
                    await ws_manager.send({
                        "type": "job_failed", "job_id": job_id,
                        "error": "Could not extract article text. The page may be paywalled or blocked.",
                    }, user_id)
                    return

                await update_job_status(job_id, "running", progress_pct=50, current_step="AI analyzing article...")
                article = await analyze_single_article(article, user_settings)

                stored = await self._store_results([article], query, job_id, user_id)
                await self._send_results(stored, query, job_id, user_id)
                await update_job_status(
                    job_id, "success", progress_pct=100, current_step="Done",
                    output_data={"total_results": len(stored)},
                )
                await ws_manager.send({
                    "type": "job_complete", "job_id": job_id, "job_type": "news_trends",
                    "result": {"total_results": len(stored)},
                }, user_id)
                return

            # ── Multi-source query search mode ───────────────────────────
            all_queries = [query]
            if expanded_queries:
                all_queries.extend(expanded_queries[:2])

            await update_job_status(
                job_id, "running", progress_pct=10,
                current_step=f"Scraping {len(sources) if sources else 12} news sources...",
            )

            from backend.services.news_scraper import _deduplicate

            async def _scrape_pass() -> list[dict]:
                tasks = [scrape_news(q, sources) for q in all_queries]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                out: list[dict] = []
                for r in results:
                    if isinstance(r, list):
                        out.extend(r)
                    elif isinstance(r, Exception):
                        logger.warning("News scrape failed for a query: %s", r)
                return _deduplicate(out)

            all_articles = await _scrape_pass()
            if not all_articles:
                logger.info(
                    "News scrape returned 0 articles for %r — retrying once after 6s",
                    query,
                )
                await update_job_status(
                    job_id, "running", progress_pct=15,
                    current_step="No articles on first pass — retrying...",
                )
                await asyncio.sleep(6)
                all_articles = await _scrape_pass()

            if not all_articles:
                await ws_manager.send_constraint_warning(
                    constraint="news_sources_empty",
                    message=(
                        f"News sources returned 0 articles for {query!r} after one retry. "
                        "Google News + Bing News RSS feeds occasionally throttle to empty "
                        "bodies; try again in 5-10 minutes or with a different query."
                    ),
                    severity="warning",
                    user_id=user_id,
                )
                await update_job_status(
                    job_id, "success", progress_pct=100, current_step="No articles found",
                    output_data={"total_results": 0},
                )
                await ws_manager.send({
                    "type": "job_complete", "job_id": job_id, "job_type": "news_trends",
                    "result": {"total_results": 0},
                }, user_id)
                return

            await update_job_status(
                job_id, "running", progress_pct=30,
                current_step=f"Found {len(all_articles)} articles, fetching full text...",
            )

            all_articles.sort(key=lambda a: a.get("engagement", 0), reverse=True)

            sem = asyncio.Semaphore(TEXT_FETCH_SEMAPHORE)
            to_fetch = all_articles[:MAX_FULL_TEXT_FETCH]

            async def _fetch_one(article):
                async with sem:
                    if article.get("full_text"):
                        return
                    data = await fetch_article_text(article["url"])
                    article["full_text"] = data.get("text")
                    article["word_count"] = data.get("word_count", 0)
                    if data.get("image") and not article.get("image_url"):
                        article["image_url"] = data["image"]

            fetch_tasks = [_fetch_one(a) for a in to_fetch]
            await asyncio.gather(*fetch_tasks, return_exceptions=True)

            with_text = sum(1 for a in to_fetch if a.get("full_text"))
            logger.info("Fetched full text for %d/%d articles", with_text, len(to_fetch))

            await update_job_status(
                job_id, "running", progress_pct=60,
                current_step=f"AI analyzing {len(to_fetch)} articles...",
            )

            try:
                analyzed = await analyze_articles(to_fetch, query, user_settings)
            except Exception as ai_err:
                logger.error("AI analysis failed for news trends: %s", ai_err)
                await update_job_status(
                    job_id, "failed",
                    error_message=f"AI analysis failed: {str(ai_err)[:200]}",
                )
                await ws_manager.send({
                    "type": "job_failed", "job_id": job_id,
                    "error": f"Found {len(to_fetch)} articles but AI analysis failed: {str(ai_err)[:150]}. Try again in a moment.",
                }, user_id)
                return

            if not analyzed:
                await update_job_status(
                    job_id, "success", progress_pct=100,
                    current_step="No high-quality articles found",
                    output_data={"total_results": 0},
                )
                await ws_manager.send({
                    "type": "job_complete", "job_id": job_id, "job_type": "news_trends",
                    "result": {"total_results": 0},
                }, user_id)
                return

            await update_job_status(
                job_id, "running", progress_pct=85,
                current_step=f"Saving {len(analyzed)} results...",
            )

            stored = await self._store_results(analyzed, query, job_id, user_id)
            await self._send_results(stored, query, job_id, user_id)

            await update_job_status(
                job_id, "success", progress_pct=100, current_step="Done",
                output_data={"total_results": len(stored)},
            )
            await ws_manager.send({
                "type": "job_complete", "job_id": job_id, "job_type": "news_trends",
                "result": {"total_results": len(stored)},
            }, user_id)

        except Exception as e:
            logger.error("News trends agent failed: %s", e, exc_info=True)
            await update_job_status(job_id, "failed", error_message=str(e))
            await ws_manager.send({
                "type": "job_failed", "job_id": job_id,
                "error": f"News research failed: {str(e)[:200]}",
            }, user_id)

    async def _store_results(
        self,
        articles: list[dict],
        query: str,
        job_id: str,
        user_id: str,
    ) -> list[dict]:
        """Store analyzed articles into TrendsResult database records."""
        stored = []
        async with AsyncSessionLocal() as db:
            for article in articles:
                url = article.get("url", "")
                video_id = hashlib.md5(url.encode()).hexdigest()[:20]

                existing = await db.execute(
                    select(TrendsResult).where(
                        TrendsResult.user_id == user_id,
                        TrendsResult.platform == "news",
                        TrendsResult.video_id == video_id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                analysis = article.get("analysis", {})
                description_json = json.dumps({
                    "full_text": article.get("full_text") or "",
                    "full_text_preview": (article.get("full_text") or "")[:500],
                    "source": article.get("source", ""),
                    "word_count": article.get("word_count", 0),
                    "engagement": article.get("engagement", 0),
                    **analysis,
                }, ensure_ascii=False)

                tr = TrendsResult(
                    user_id=user_id,
                    job_id=job_id,
                    platform="news",
                    video_id=video_id,
                    video_url=url,
                    title=article.get("title", "Untitled"),
                    description=description_json,
                    author=article.get("source_domain", ""),
                    thumbnail_url=article.get("image_url"),
                    views=article.get("engagement", 0),
                    virality_score=article.get("virality_score", 0),
                    niche=query,
                    upload_date=article.get("published_at"),
                )
                db.add(tr)
                await db.flush()

                stored.append({
                    "id": tr.id,
                    "title": tr.title,
                    "source_domain": article.get("source_domain", ""),
                    "url": url,
                    "image_url": article.get("image_url"),
                    "published_at": article.get("published_at").isoformat() if article.get("published_at") else None,
                    "word_count": article.get("word_count", 0),
                    "virality_score": article.get("virality_score", 0),
                    "engagement": article.get("engagement", 0),
                    "analysis": analysis,
                })

            await db.commit()

        return stored

    async def _ai_extract_text(self, url: str, user_settings=None) -> str | None:
        from backend.services.news_scraper import _fetch_html
        try:
            html = await _fetch_html(url)
            if not html:
                return None

            import re as _re
            clean = _re.sub(r'<(script|style|nav|footer|header|svg|noscript)[^>]*>.*?</\1>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
            text_only = _re.sub(r'<[^>]+>', ' ', clean)
            text_only = _re.sub(r'\s+', ' ', text_only).strip()

            if len(text_only) < 100:
                return None

            truncated = text_only[:8000]
            from backend.core.ai_provider import get_ai_client
            prompt = (
                "Extract ONLY the main article text from this web page content. "
                "Remove all navigation, ads, sidebars, comments, related articles, and boilerplate. "
                "Return ONLY the clean article text, nothing else. No commentary, no labels, no formatting instructions.\n\n"
                f"Page content:\n{truncated}"
            )

            ai = get_ai_client(user_settings)
            response = await ai.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
            )
            if response and len(response) > 100:
                logger.info("AI extracted %d chars from %s", len(response), url[:60])
                return response.strip()

        except Exception as e:
            logger.warning("AI text extraction failed for %s: %s", url[:60], e)
        return None

    async def _send_results(
        self,
        stored: list[dict],
        query: str,
        job_id: str,
        user_id: str,
    ):
        await ws_manager.send({
            "type": "news_results",
            "job_id": job_id,
            "total": len(stored),
            "query": query,
            "results": stored,
        }, user_id)


async def run_news_trends(
    job_id: str,
    query: str,
    expanded_queries: list[str] | None = None,
    sources: list[str] | None = None,
    direct_url: str | None = None,
    user_id: str = "local",
):
    await NewsTrendsAgent().run(
        job_id=job_id,
        query=query,
        expanded_queries=expanded_queries,
        sources=sources,
        direct_url=direct_url,
        user_id=user_id,
    )


# Backward compatibility aliases
NewsScoutAgent = NewsTrendsAgent
run_news_scout = run_news_trends
