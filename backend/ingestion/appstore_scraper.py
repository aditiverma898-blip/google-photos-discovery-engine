"""
App Store Scraper — Pulls Google Photos reviews from Google Play Store and Apple App Store.

Uses: google-play-scraper (Python), Apple RSS feed fallback
Target: 3,000–4,000 records
Filters: 1–3 star reviews containing search/retrieval failure keywords
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from google_play_scraper import Sort, reviews as gplay_reviews, reviews_all
except ImportError:
    gplay_reviews = None
    reviews_all = None
    logger.warning("google-play-scraper not installed. Run: pip install google-play-scraper")

try:
    import aiohttp
except ImportError:
    aiohttp = None

from ingestion.base_scraper import BaseScraper


# User-Agent rotation for resilience
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
]

# Google Photos app IDs
GOOGLE_PHOTOS_PLAY_STORE_ID = "com.google.android.apps.photos"
GOOGLE_PHOTOS_APP_STORE_ID = "962194608"  # Apple App Store


class AppStoreScraper(BaseScraper):
    """Scrape Google Photos reviews from Google Play and Apple App Store."""

    MAX_CONCURRENT_REQUESTS = 1  # Be gentle with app stores
    BATCH_SIZE = 500

    # Keywords indicating a search/retrieval failure
    RELEVANCE_KEYWORDS = [
        "find", "search", "lost", "missing", "remember", "looking for",
        "can't find", "cannot find", "couldn't find", "where is",
        "disappeared", "gone", "scroll", "browse", "retrieve",
        "not showing", "won't show", "doesn't show", "not appearing",
        "hard to find", "impossible to find", "old photo", "old picture",
    ]

    @property
    def source_name(self) -> str:
        return "appstore"

    async def scrape(self):
        """Main scrape generator — pulls from both Play Store and App Store."""
        # 1. Google Play Store reviews
        async for record in self._scrape_play_store():
            yield record

        # 2. Apple App Store reviews
        async for record in self._scrape_app_store():
            yield record

    # ─── Google Play Store ─────────────────────────────────────────

    async def _scrape_play_store(self):
        """
        Scrape Google Play Store reviews for Google Photos.
        Iterates across multiple countries and sort strategies to maximize volume.
        """
        if gplay_reviews is None:
            logger.warning("[appstore] google-play-scraper not installed, skipping Play Store")
            return

        logger.info("[appstore] Starting Google Play Store scrape...")

        countries = ["us", "gb", "ca", "in", "au", "de", "fr", "sg", "ph", "nz"]
        sort_strategies = [Sort.NEWEST, Sort.MOST_RELEVANT]
        score_filters = [1, 2, 3]
        total_fetched = 0
        loop = asyncio.get_event_loop()

        for country in countries:
            for sort_strategy in sort_strategies:
                for score_filt in score_filters:
                    sort_name = "NEWEST" if sort_strategy == Sort.NEWEST else "MOST_RELEVANT"
                    logger.info(f"[appstore] Play Store: scraping country={country}, sort={sort_name}, score={score_filt}")
                    continuation_token = None
                    page = 0

                    while True:
                        try:
                            cur_token = continuation_token
                            result, token = await loop.run_in_executor(
                                None,
                                lambda t=cur_token, c=country, s=sort_strategy, sf=score_filt: gplay_reviews(
                                    GOOGLE_PHOTOS_PLAY_STORE_ID,
                                    lang="en",
                                    country=c,
                                    sort=s,
                                    count=200,
                                    filter_score_with=sf,
                                    continuation_token=t,
                                ),
                            )
                        except Exception as e:
                            logger.warning(f"[appstore] Play Store error ({country}/{sort_name}/score {score_filt}) page {page}: {e}")
                            break

                        if not result:
                            break

                        page += 1
                        relevant_count = 0

                        for review in result:
                            score = review.get("score", 5)
                            content = review.get("content", "")

                            # Filter: 1–3 stars AND contains relevant keywords
                            if score <= 3 and content and self.keyword_match(content, self.RELEVANCE_KEYWORDS):
                                review_id = review.get("reviewId", "")
                                yield {
                                    "raw_text": content,
                                    "url_id": f"play_store_{GOOGLE_PHOTOS_PLAY_STORE_ID}_{country}_{score_filt}_{review_id}",
                                    "metadata": {
                                        "store": "google_play",
                                        "app_id": GOOGLE_PHOTOS_PLAY_STORE_ID,
                                        "country": country,
                                        "score": score,
                                        "thumbs_up": review.get("thumbsUpCount", 0),
                                        "review_created": str(review.get("at", "")),
                                        "reply": review.get("replyContent", ""),
                                        "app_version": review.get("appVersion", ""),
                                    },
                                }
                                relevant_count += 1

                            # Also capture 4-5 star reviews that mention search issues
                            elif score >= 4 and content and any(
                                kw in content.lower() for kw in ["can't find", "search broken", "search not working"]
                            ):
                                review_id = review.get("reviewId", "")
                                yield {
                                    "raw_text": content,
                                    "url_id": f"play_store_{GOOGLE_PHOTOS_PLAY_STORE_ID}_{country}_{score_filt}_{review_id}",
                                    "metadata": {
                                        "store": "google_play",
                                        "app_id": GOOGLE_PHOTOS_PLAY_STORE_ID,
                                        "country": country,
                                        "score": score,
                                        "thumbs_up": review.get("thumbsUpCount", 0),
                                        "review_created": str(review.get("at", "")),
                                        "app_version": review.get("appVersion", ""),
                                        "note": "high_score_but_search_complaint",
                                    },
                                }
                                relevant_count += 1

                        total_fetched += len(result)
                        continuation_token = token

                        logger.info(
                            f"[appstore] Play Store ({country}/{sort_name}/score {score_filt}) page {page}: {len(result)} reviews, "
                            f"{relevant_count} relevant | Total fetched: {total_fetched}"
                        )

                        await asyncio.sleep(random.uniform(0.5, 1.2))

                        if not token or page >= 40:
                            break

        logger.info(f"[appstore] Play Store complete: {total_fetched} total reviews processed")

    # ─── Apple App Store ───────────────────────────────────────────

    async def _scrape_app_store(self):
        """
        Scrape Apple App Store reviews for Google Photos.
        Uses the iTunes RSS feed (JSON) which provides up to 500 recent reviews.
        Also tries multiple country codes for more volume.
        """
        if aiohttp is None:
            logger.warning("[appstore] aiohttp not installed, skipping App Store")
            return

        logger.info("[appstore] Starting Apple App Store scrape...")

        countries = ["us", "gb", "ca", "au", "in", "de", "fr", "jp", "br", "mx"]

        async with aiohttp.ClientSession() as session:
            for country in countries:
                async for record in self._scrape_app_store_country(session, country):
                    yield record

    async def _scrape_app_store_country(self, session, country: str):
        """Scrape App Store reviews for a specific country."""
        logger.info(f"[appstore] App Store: scraping country={country}")

        for page in range(1, 11):  # Pages 1–10
            url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews/"
                f"page={page}/id={GOOGLE_PHOTOS_APP_STORE_ID}/sortby=mostrecent/json"
            )

            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}

                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 403:
                        logger.warning(f"[appstore] App Store blocked (403) for {country} page {page}")
                        break
                    if resp.status == 404:
                        # No more pages
                        break
                    if resp.status != 200:
                        logger.warning(f"[appstore] App Store HTTP {resp.status} for {country} page {page}")
                        break

                    data = await resp.json(content_type=None)

                feed = data.get("feed", {})
                entries = feed.get("entry", [])

                if not entries:
                    break

                relevant_count = 0
                for entry in entries:
                    # Skip the first entry if it's the app metadata
                    if "im:rating" not in entry:
                        continue

                    rating = int(entry.get("im:rating", {}).get("label", "5"))
                    title = entry.get("title", {}).get("label", "")
                    content = entry.get("content", {}).get("label", "")
                    author = entry.get("author", {}).get("name", {}).get("label", "")
                    review_id = entry.get("id", {}).get("label", "")
                    app_version = entry.get("im:version", {}).get("label", "")

                    full_text = f"{title}\n{content}".strip()

                    # Filter: 1–3 stars AND relevant keywords
                    if rating <= 3 and full_text and self.keyword_match(full_text, self.RELEVANCE_KEYWORDS):
                        yield {
                            "raw_text": full_text,
                            "url_id": f"app_store_{GOOGLE_PHOTOS_APP_STORE_ID}_{review_id}_{country}",
                            "metadata": {
                                "store": "apple_app_store",
                                "app_id": GOOGLE_PHOTOS_APP_STORE_ID,
                                "country": country,
                                "score": rating,
                                "app_version": app_version,
                                "author": author,
                            },
                        }
                        relevant_count += 1

                logger.debug(
                    f"[appstore] App Store {country} page {page}: "
                    f"{len(entries)} entries, {relevant_count} relevant"
                )

                # Rate limiting
                await asyncio.sleep(random.uniform(1.0, 2.5))

            except asyncio.TimeoutError:
                logger.warning(f"[appstore] App Store timeout for {country} page {page}")
                break
            except Exception as e:
                logger.warning(f"[appstore] App Store error for {country} page {page}: {e}")
                await asyncio.sleep(3.0)
                continue

    # ─── Supplementary: Play Store by Country ──────────────────────

    async def scrape_play_store_countries(self, countries: list[str] = None):
        """
        Supplementary: scrape Play Store reviews from additional countries.
        Use if initial scrape doesn't yield enough volume.
        """
        if gplay_reviews is None:
            return

        countries = countries or ["gb", "in", "de", "fr", "br", "ca", "au"]
        loop = asyncio.get_event_loop()

        for country in countries:
            logger.info(f"[appstore] Play Store supplementary: country={country}")
            try:
                result, _ = await loop.run_in_executor(
                    None,
                    lambda c=country: gplay_reviews(
                        GOOGLE_PHOTOS_PLAY_STORE_ID,
                        lang="en",
                        country=c,
                        sort=Sort.MOST_RELEVANT,
                        count=500,
                        filter_score_with=None,
                    ),
                )

                for review in result:
                    score = review.get("score", 5)
                    content = review.get("content", "")
                    if score <= 3 and content and self.keyword_match(content, self.RELEVANCE_KEYWORDS):
                        yield {
                            "raw_text": content,
                            "url_id": f"play_store_{GOOGLE_PHOTOS_PLAY_STORE_ID}_{review.get('reviewId', '')}_{country}",
                            "metadata": {
                                "store": "google_play",
                                "country": country,
                                "score": score,
                                "thumbs_up": review.get("thumbsUpCount", 0),
                            },
                        }

                await asyncio.sleep(random.uniform(2.0, 4.0))

            except Exception as e:
                logger.warning(f"[appstore] Play Store {country} error: {e}")
                continue
