# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial trends velocity tracking service — proactive momentum & surge detection.
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from typing import Optional

from sqlalchemy import and_, select

from backend.core.http_utils import get_user_agent
from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class TrendsAlert:
    """Represents a trending velocity alert on search interest."""
    keyword: str
    current_interest: float      # Present relative volume (0-100)
    baseline_interest: float     # Historical baseline average
    velocity_multiplier: float   # Ratio over baseline (e.g. 2.5x)
    alert_level: str             # "spike" | "rising" | "steady" | "declining"


# Backward compatibility alias
TrendAlert = TrendsAlert


async def check_keyword_trends_velocity(keyword: str) -> TrendsAlert:
    """
    Measure 7-day search momentum using Google Trends data.
    Classifies volume acceleration as spike, rising, steady, or declining.
    """
    def _query_trends():
        try:
            from pytrends.request import TrendReq
            req = TrendReq(hl="en-US", tz=360)
            req.build_payload([keyword], timeframe="now 7-d")
            df = req.interest_over_time()

            if df.empty or keyword not in df.columns:
                return TrendsAlert(
                    keyword=keyword,
                    current_interest=0,
                    baseline_interest=0,
                    velocity_multiplier=1.0,
                    alert_level="steady",
                )

            data = df[keyword].tolist()
            if len(data) < 2:
                val = data[0] if data else 0
                return TrendsAlert(
                    keyword=keyword,
                    current_interest=val,
                    baseline_interest=val,
                    velocity_multiplier=1.0,
                    alert_level="steady",
                )

            split = max(1, int(len(data) * 0.75))
            baseline = sum(data[:split]) / max(split, 1)
            current = sum(data[split:]) / max(len(data) - split, 1)
            velocity = current / max(baseline, 1)

            if velocity >= 3.0:
                level = "spike"
            elif velocity >= 1.5:
                level = "rising"
            elif velocity >= 0.8:
                level = "steady"
            else:
                level = "declining"

            return TrendsAlert(
                keyword=keyword,
                current_interest=round(current, 1),
                baseline_interest=round(baseline, 1),
                velocity_multiplier=round(velocity, 2),
                alert_level=level,
            )
        except Exception as err:
            logger.warning(f"Trends velocity calculation failed for '{keyword}': {err}")
            return TrendsAlert(
                keyword=keyword,
                current_interest=0,
                baseline_interest=0,
                velocity_multiplier=1.0,
                alert_level="steady",
            )

    return await asyncio.to_thread(_query_trends)


# Compatibility alias
check_keyword_velocity = check_keyword_trends_velocity


async def check_user_keywords_velocity(user_id: str = "local") -> list[TrendsAlert]:
    """
    Evaluate velocity across user's recent searched niches and broadcast alerts.
    """
    from backend.core.ws_manager import ws_manager
    from backend.models.user_behavior import UserBehavior

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(UserBehavior)
            .where(
                and_(
                    UserBehavior.user_id == user_id,
                    UserBehavior.event_type.in_(["niche_searched", "trend_searched", "trends_searched"]),
                    UserBehavior.created_at >= datetime.utcnow() - timedelta(days=30),
                )
            )
            .order_by(UserBehavior.created_at.desc())
            .limit(50)
        )
        events = res.scalars().all()

    niches = set()
    for e in events:
        try:
            d = json.loads(e.data_json or "{}")
            if d.get("niche"):
                niches.add(d["niche"])
        except (json.JSONDecodeError, TypeError):
            pass

    if not niches:
        return []

    alerts: list[TrendsAlert] = []
    for keyword in list(niches)[:5]:
        alert = await check_keyword_trends_velocity(keyword)
        if alert.alert_level in ("spike", "rising"):
            alerts.append(alert)
            payload = {
                "type": "trends_alert",
                "keyword": alert.keyword,
                "alert_level": alert.alert_level,
                "velocity": alert.velocity_multiplier,
                "current_interest": alert.current_interest,
                "baseline_interest": alert.baseline_interest,
                "message": (
                    f"'{alert.keyword}' is {alert.alert_level.upper()}! "
                    f"{alert.velocity_multiplier}x above baseline. "
                    f"Explore trends in this niche now for early-mover advantage."
                ),
            }
            await ws_manager.send(payload, user_id)
            # Duplicate with trend_alert type for backwards-compatible frontend subscribers
            await ws_manager.send({**payload, "type": "trend_alert"}, user_id)

        await asyncio.sleep(1)

    return alerts


async def get_trending_keywords(keywords: list[str]) -> list[dict]:
    """Fetch velocity scores for a list of target keywords, descending order."""
    results = []
    for kw in keywords[:10]:
        alert = await check_keyword_trends_velocity(kw)
        results.append({
            "keyword": alert.keyword,
            "current_interest": alert.current_interest,
            "baseline_interest": alert.baseline_interest,
            "velocity": alert.velocity_multiplier,
            "alert_level": alert.alert_level,
        })
        await asyncio.sleep(0.5)

    results.sort(key=lambda x: x["velocity"], reverse=True)
    return results


async def cross_platform_correlation(keyword: str) -> dict:
    """
    Correlate momentum for a keyword across Google Trends, YouTube, and Reddit.
    High multi-platform agreement generates a high confidence viral signal.
    """
    g_task = asyncio.create_task(check_keyword_trends_velocity(keyword))
    yt_task = asyncio.create_task(_evaluate_youtube_presence(keyword))
    rd_task = asyncio.create_task(_evaluate_reddit_presence(keyword))

    google_alert, yt_signal, rd_signal = await asyncio.gather(g_task, yt_task, rd_task)

    signals = []
    platforms_trending = []

    if google_alert.alert_level in ("spike", "rising"):
        signals.append(("google_trends", google_alert.velocity_multiplier))
        platforms_trending.append("google_trends")

    if yt_signal.get("is_trending"):
        signals.append(("youtube", yt_signal.get("recency_score", 1.0)))
        platforms_trending.append("youtube")

    if rd_signal.get("is_trending"):
        signals.append(("reddit", rd_signal.get("engagement_score", 1.0)))
        platforms_trending.append("reddit")

    momentum = len(platforms_trending)
    if momentum >= 3:
        confidence = "very_high"
    elif momentum == 2:
        confidence = "high"
    elif momentum == 1:
        confidence = "moderate"
    else:
        confidence = "low"

    combined = 0
    if signals:
        avg_signal = sum(s[1] for s in signals) / len(signals)
        combined = min(avg_signal * momentum * 15, 100)

    return {
        "keyword": keyword,
        "cross_platform_score": round(combined, 1),
        "confidence": confidence,
        "platforms_trending": platforms_trending,
        "platform_count": momentum,
        "google_trends": {
            "velocity": google_alert.velocity_multiplier,
            "alert_level": google_alert.alert_level,
            "current_interest": google_alert.current_interest,
        },
        "youtube": yt_signal,
        "reddit": rd_signal,
    }


async def _evaluate_youtube_presence(keyword: str) -> dict:
    import httpx
    from backend.config import settings as env
    api_key = env.YOUTUBE_API_KEY
    if not api_key:
        return {"is_trending": False, "reason": "no_api_key"}

    def _call():
        try:
            resp = httpx.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "order": "date",
                    "publishedAfter": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "maxResults": 10,
                    "key": api_key,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                return {"is_trending": False, "reason": "api_error"}
            data = resp.json()
            total = data.get("pageInfo", {}).get("totalResults", 0)
            items = data.get("items", [])
            return {
                "is_trending": total > 50,
                "recent_videos_count": total,
                "recency_score": round(min(total / 100.0, 3.0), 2),
                "sample_titles": [i["snippet"]["title"] for i in items[:3]],
            }
        except Exception as ex:
            logger.warning(f"YouTube velocity signal check failed for '{keyword}': {ex}")
            return {"is_trending": False, "reason": str(ex)}

    return await asyncio.to_thread(_call)


async def _evaluate_reddit_presence(keyword: str) -> dict:
    import httpx

    def _call():
        try:
            resp = httpx.get(
                "https://www.reddit.com/search.json",
                params={"q": keyword, "sort": "new", "t": "week", "limit": 10},
                headers={"User-Agent": get_user_agent()},
                timeout=10,
            )
            if resp.status_code != 200:
                return {"is_trending": False, "reason": "api_error"}
            posts = resp.json().get("data", {}).get("children", [])
            if not posts:
                return {"is_trending": False, "post_count": 0, "engagement_score": 0}

            total_score = sum(p["data"].get("score", 0) for p in posts)
            total_comments = sum(p["data"].get("num_comments", 0) for p in posts)
            avg_score = total_score / len(posts)
            return {
                "is_trending": avg_score > 100 or len(posts) >= 8,
                "post_count": len(posts),
                "avg_score": round(avg_score, 1),
                "total_comments": total_comments,
                "engagement_score": round(min(avg_score / 200.0 + len(posts) / 10.0, 3.0), 2),
            }
        except Exception as ex:
            logger.warning(f"Reddit velocity signal check failed for '{keyword}': {ex}")
            return {"is_trending": False, "reason": str(ex)}

    return await asyncio.to_thread(_call)


# Backward compatibility aliases
TrendAlert = TrendsAlert
check_keyword_velocity = check_keyword_trends_velocity
_check_youtube_signal = _evaluate_youtube_presence
_check_reddit_signal = _evaluate_reddit_presence

