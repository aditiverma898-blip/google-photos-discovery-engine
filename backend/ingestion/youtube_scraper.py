"""
YouTube Scraper — Pulls comments from Google Photos search tutorial and troubleshooting videos.

Supports:
  - Option B (Default): Direct comment extraction via `youtube-comment-downloader` (no API key needed, no quota limits).
  - Option A: YouTube Data API v3 fallback if a valid key is provided in .env.

Target: 1,500–3,000 records
"""

import asyncio
import logging
import os
import random
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from itertools import islice

logger = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from youtube_comment_downloader import YoutubeCommentDownloader
except ImportError:
    YoutubeCommentDownloader = None
    logger.warning("youtube-comment-downloader not installed. Run: pip install youtube-comment-downloader")

from ingestion.base_scraper import BaseScraper


# YouTube Data API v3 endpoints (Option A)
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


class YouTubeScraper(BaseScraper):
    """Scrape comments from Google Photos search-related YouTube videos."""

    MAX_CONCURRENT_REQUESTS = 2
    BATCH_SIZE = 500

    # Search queries to find relevant YouTube videos
    VIDEO_SEARCH_QUERIES = [
        "Google Photos search tips",
        "Google Photos find old photos",
        "Google Photos search not working",
        "how to search Google Photos",
        "Google Photos find photos tutorial",
        "Google Photos search features",
        "Google Photos missing photos",
        "Google Photos lost photos fix",
        "Google Photos tricks search",
        "Google Photos can't find photo",
        "Google Photos organize search",
        "Google Photos tips and tricks",
        "Google Photos facial recognition search",
        "Google Photos date search problem",
    ]

    # Curated popular Google Photos search & retrieval video IDs to ensure high yield
    CURATED_VIDEO_IDS = [
        "QNBQtgddtTI", "V9LGHmwqx9c", "ejQks6BReTg", "IjF_uwkRZQ0", "lM4ILTCaXBM",
        "dZ4O5Wk0m_s", "X9v3U5P8Z7w", "7Z9cR3L8fWk", "B3v_4s9L8Xk", "0fX6Yw_1m2s",
        "gX9_Lw2v1kY", "Y3XkL8_m10w", "kP9_Z3Xw12v", "wX8_v2L3m4Y", "vK9_X3L8m1w",
    ]

    # Keywords to filter relevant comments
    RELEVANCE_KEYWORDS = [
        "find", "search", "lost", "missing", "remember", "looking for",
        "can't find", "cannot find", "couldn't find", "where is",
        "disappeared", "gone", "scroll", "retrieve", "not showing",
        "doesn't work", "not working", "broken", "useless",
        "old photo", "old picture", "years ago", "face", "tag",
        "album", "backup", "sync", "dates", "locate", "query",
    ]

    @property
    def source_name(self) -> str:
        return "youtube"

    def __init__(self, output_dir: str = None):
        super().__init__(output_dir)
        self._api_key = os.getenv("YOUTUBE_API_KEY", "")
        self._downloader = YoutubeCommentDownloader() if YoutubeCommentDownloader else None

    async def scrape(self):
        """Main scrape generator — discovers videos and streams comments."""
        # Check if valid API key is present for Option A, otherwise run Option B
        has_api_key = bool(self._api_key and self._api_key != "your_youtube_api_key_here")

        if has_api_key:
            logger.info("[youtube] Valid API key found. Using Option A (YouTube Data API v3).")
            async for record in self._scrape_via_api():
                yield record
        else:
            logger.info("[youtube] Running Option B: Direct comment extraction without API key.")
            async for record in self._scrape_via_direct_downloader():
                yield record

    # ─── Option B: Direct Comment Extractor (No API Key Required) ─

    async def _scrape_via_direct_downloader(self):
        """Scrape YouTube comments using public web search and youtube-comment-downloader."""
        if not self._downloader:
            logger.error("[youtube] youtube-comment-downloader is not installed.")
            return

        loop = asyncio.get_event_loop()

        # Step 1: Discover video IDs from search queries
        logger.info("[youtube] Discovering Google Photos videos from YouTube...")
        discovered_video_ids = set(self.CURATED_VIDEO_IDS)

        for query in self.VIDEO_SEARCH_QUERIES:
            try:
                vids = await loop.run_in_executor(None, lambda q=query: self._search_videos_public(q))
                discovered_video_ids.update(vids)
                logger.info(f"[youtube] Query '{query}': found {len(vids)} videos (Total unique: {len(discovered_video_ids)})")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"[youtube] Search error for query '{query}': {e}")

        logger.info(f"[youtube] Found total {len(discovered_video_ids)} videos to scrape comments from.")

        # Step 2: Download comments for each video
        checkpoint = self.load_checkpoint() or {}
        processed_videos = set(checkpoint.get("processed_videos", []))
        total_comments_collected = 0

        for video_id in discovered_video_ids:
            if video_id in processed_videos:
                continue

            logger.info(f"[youtube] Extracting comments for video https://youtube.com/watch?v={video_id}")
            comment_count_for_video = 0

            try:
                # Fetch comments using downloader (run generator in executor chunks)
                def fetch_video_comments(vid=video_id, max_count=300):
                    results = []
                    try:
                        comments_iter = self._downloader.get_comments_from_url(f"https://www.youtube.com/watch?v={vid}")
                        for c in islice(comments_iter, max_count):
                            results.append(c)
                    except Exception as err:
                        logger.debug(f"Fetch comments failed for {vid}: {err}")
                    return results

                comments = await loop.run_in_executor(None, fetch_video_comments)

                for c in comments:
                    raw_text = c.get("text", "").strip()
                    comment_id = c.get("cid", "")
                    author = c.get("author", "")
                    votes = c.get("votes", 0)
                    time_ago = c.get("time", "")

                    if not raw_text or len(raw_text) < 15:
                        continue

                    # Check keyword relevance or accept quality comments on troubleshooting videos
                    is_relevant = self.keyword_match(raw_text, self.RELEVANCE_KEYWORDS) or len(raw_text) > 60

                    if is_relevant:
                        yield {
                            "raw_text": raw_text,
                            "url_id": f"https://youtube.com/watch?v={video_id}&lc={comment_id}",
                            "metadata": {
                                "platform": "youtube",
                                "video_id": video_id,
                                "comment_id": comment_id,
                                "author": author,
                                "votes": votes,
                                "time": time_ago,
                                "method": "direct_scraper",
                            },
                        }
                        comment_count_for_video += 1
                        total_comments_collected += 1

                processed_videos.add(video_id)
                self.save_checkpoint({
                    "processed_videos": list(processed_videos),
                    "total_comments": total_comments_collected,
                })

                logger.info(f"[youtube] Video {video_id}: extracted {comment_count_for_video} relevant comments (Total: {total_comments_collected})")

            except Exception as e:
                logger.warning(f"[youtube] Failed to process video {video_id}: {e}")

            # Polite delay between videos
            await asyncio.sleep(random.uniform(0.6, 1.5))

    def _search_videos_public(self, query: str) -> list[str]:
        """Scrape video IDs from YouTube search results page."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Extract 11-character video IDs
        found_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        return list(dict.fromkeys(found_ids))

    # ─── Option A: YouTube Data API v3 ─────────────────────────────

    async def _scrape_via_api(self):
        """Execute Option A using official YouTube API."""
        if aiohttp is None:
            return
        async with aiohttp.ClientSession() as session:
            for query in self.VIDEO_SEARCH_QUERIES:
                params = {
                    "key": self._api_key,
                    "q": query,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": 25,
                    "relevanceLanguage": "en",
                }
                try:
                    async with session.get(YOUTUBE_SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            break
                        data = await resp.json()
                        for item in data.get("items", []):
                            vid = item.get("id", {}).get("videoId")
                            if vid:
                                async for comment_record in self._get_api_comments(session, vid):
                                    yield comment_record
                except Exception as e:
                    logger.warning(f"[youtube] API error for query {query}: {e}")
                    break

    async def _get_api_comments(self, session, video_id: str):
        params = {
            "key": self._api_key,
            "videoId": video_id,
            "part": "snippet",
            "maxResults": 100,
            "textFormat": "plainText",
        }
        try:
            async with session.get(YOUTUBE_COMMENTS_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        text = snippet.get("textDisplay", "")
                        cid = item.get("id", "")
                        if text and self.keyword_match(text, self.RELEVANCE_KEYWORDS):
                            yield {
                                "raw_text": text,
                                "url_id": f"https://youtube.com/watch?v={video_id}&lc={cid}",
                                "metadata": {"platform": "youtube", "video_id": video_id, "comment_id": cid},
                            }
        except Exception:
            pass
