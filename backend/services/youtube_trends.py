# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial YouTube trends discovery service.
import asyncio
from datetime import datetime, timedelta
import logging
import re
from typing import Optional
import unicodedata

logger = logging.getLogger(__name__)


def _detect_query_language(text: str) -> str:
    """Detect language profile of the search query for relevance tuning."""
    cjk = 0
    for ch in text:
        name = unicodedata.name(ch, "")
        if "CJK" in name or "HIRAGANA" in name or "KATAKANA" in name:
            cjk += 1
    if cjk > 0:
        has_kana = any("HIRAGANA" in unicodedata.name(c, "") or "KATAKANA" in unicodedata.name(c, "") for c in text)
        return "ja" if has_kana else "zh"
    if any("\uAC00" <= ch <= "\uD7A3" or "\u1100" <= ch <= "\u11FF" for ch in text):
        return "ko"
    return "en"


def _format_search_cutoff(days: int = 30) -> str:
    """Compute ISO timestamp cutoff for trending video recency."""
    dt = datetime.utcnow() - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_duration(duration_str: str) -> Optional[int]:
    """Convert ISO-8601 duration string (e.g. PT1H4M20S) to total seconds."""
    if not duration_str:
        return None
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(seconds or 0)


def _parse_publish_date(date_str: str) -> Optional[datetime]:
    """Parse YouTube API timestamp into naive UTC datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _parse_relative_time(text: str) -> datetime:
    """Parse relative time string (e.g. '3 days ago', '14 hours ago') into UTC datetime."""
    now = datetime.utcnow()
    if not text:
        return now
    t = text.lower().strip()
    m_hour = re.search(r"(\d+)\s*(?:hour|hr|h)\b", t)
    if m_hour:
        return now - timedelta(hours=int(m_hour.group(1)))
    m_day = re.search(r"(\d+)\s*(?:day|d)\b", t)
    if m_day:
        return now - timedelta(days=int(m_day.group(1)))
    m_week = re.search(r"(\d+)\s*(?:week|w)\b", t)
    if m_week:
        return now - timedelta(days=int(m_week.group(1)) * 7)
    m_month = re.search(r"(\d+)\s*(?:month|m)\b", t)
    if m_month:
        return now - timedelta(days=int(m_month.group(1)) * 30)
    m_min = re.search(r"(\d+)\s*(?:minute|min|m)\b", t)
    if m_min:
        return now - timedelta(minutes=int(m_min.group(1)))
    return now


def _parse_views_string(text: str) -> int:
    """Parse view count text (e.g. '65,288 views', '1.2M views') into integer."""
    if not text:
        return 0
    m_m = re.search(r"([\d\.]+)\s*m\b", text, re.I)
    if m_m:
        return int(float(m_m.group(1)) * 1_000_000)
    m_k = re.search(r"([\d\.]+)\s*k\b", text, re.I)
    if m_k:
        return int(float(m_k.group(1)) * 1_000)
    m_num = re.search(r"(\d[\d\s,\.]*)", text)
    if m_num:
        clean = re.sub(r"[^\d]", "", m_num.group(1))
        return int(clean) if clean else 0
    return 0


def _search_youtube_public_recent(niche: str, max_results: int = 50) -> list[dict]:
    """Search YouTube for recent videos (this month) via public endpoint without API key."""
    import json
    import urllib.parse
    import urllib.request

    query_encoded = urllib.parse.quote_plus(niche)
    # sp=EgQIAxAB filters strictly for videos uploaded this month
    url = f"https://www.youtube.com/results?search_query={query_encoded}&sp=EgQIAxAB"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
        idx = html.find("ytInitialData =")
        if idx == -1:
            return []
        end = html.find(";</script>", idx)
        data = json.loads(html[idx + len("ytInitialData ="):end].strip())

        contents = (
            data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )
        trends = []
        for sec in contents:
            items = sec.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                v = item.get("videoRenderer")
                if not v:
                    continue
                vid = v.get("videoId")
                if not vid:
                    continue
                title = v.get("title", {}).get("runs", [{}])[0].get("text", "")
                pub_text = v.get("publishedTimeText", {}).get("simpleText", "")
                view_text = v.get("viewCountText", {}).get("simpleText", "")
                uploader = v.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                uploader_nav = (
                    v.get("ownerText", {})
                    .get("runs", [{}])[0]
                    .get("navigationEndpoint", {})
                    .get("browseEndpoint", {})
                    .get("browseId", "")
                )
                thumbs = v.get("thumbnail", {}).get("thumbnails", [])
                thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                length_text = v.get("lengthText", {}).get("simpleText", "")

                duration_s = None
                if length_text:
                    parts = [int(p) for p in length_text.split(":") if p.isdigit()]
                    if len(parts) == 2:
                        duration_s = parts[0] * 60 + parts[1]
                    elif len(parts) == 3:
                        duration_s = parts[0] * 3600 + parts[1] * 60 + parts[2]

                trends.append({
                    "platform": "youtube",
                    "requested_platform": "youtube",
                    "video_id": vid,
                    "video_url": f"https://youtube.com/watch?v={vid}",
                    "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
                    "title": title,
                    "description": "",
                    "author": uploader,
                    "author_url": f"https://youtube.com/channel/{uploader_nav}" if uploader_nav else "",
                    "thumbnail_url": thumb_url,
                    "views": _parse_views_string(view_text),
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "duration_seconds": duration_s,
                    "upload_date": _parse_relative_time(pub_text),
                })
                if len(trends) >= max_results:
                    break
            if len(trends) >= max_results:
                break
        return trends
    except Exception as ex:
        logger.warning("YouTube public recency search failed: %s", ex)
        return []


async def search_youtube_trends(
    niche: str,
    api_key: Optional[str] = None,
    max_results: int = 50,
) -> list[dict]:
    """
    Search YouTube for high-velocity trending videos in a given niche.
    Ensures recency by filtering strictly for videos uploaded in the past 30 days.
    """
    if api_key:
        try:
            from googleapiclient.discovery import build

            def _execute_search():
                client = build("youtube", "v3", developerKey=api_key)
                lang = _detect_query_language(niche)

                search_query = client.search().list(
                    q=niche,
                    part="id,snippet",
                    type="video",
                    order="viewCount",
                    maxResults=min(max_results, 50),
                    publishedAfter=_format_search_cutoff(30),
                    relevanceLanguage=lang,
                )
                search_resp = search_query.execute()

                video_ids = [
                    item["id"]["videoId"]
                    for item in search_resp.get("items", [])
                    if item.get("id", {}).get("videoId")
                ]
                if not video_ids:
                    return []

                videos_query = client.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=",".join(video_ids),
                )
                videos_resp = videos_query.execute()

                trends = []
                for item in videos_resp.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    content = item.get("contentDetails", {})
                    vid = item.get("id", "")

                    trends.append({
                        "platform": "youtube",
                        "video_id": vid,
                        "video_url": f"https://youtube.com/watch?v={vid}",
                        "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", "")[:500],
                        "author": snippet.get("channelTitle", ""),
                        "author_url": f"https://youtube.com/channel/{snippet.get('channelId', '')}",
                        "thumbnail_url": (
                            snippet.get("thumbnails", {}).get("maxres", {}).get("url")
                            or snippet.get("thumbnails", {}).get("standard", {}).get("url")
                            or snippet.get("thumbnails", {}).get("high", {}).get("url")
                            or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                        ),
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "shares": 0,
                        "duration_seconds": _parse_iso_duration(content.get("duration", "")),
                        "upload_date": _parse_publish_date(snippet.get("publishedAt")),
                    })
                return trends

            res = await asyncio.to_thread(_execute_search)
            if res:
                return res
        except Exception as api_err:
            logger.warning("YouTube Data API call error (%s) — falling back to public recency search", api_err)

    # Public recency search (no API key required, strictly recent this month)
    return await asyncio.to_thread(_search_youtube_public_recent, niche, max_results)


# Compatibility aliases
search_youtube = search_youtube_trends

