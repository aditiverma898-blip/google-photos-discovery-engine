"""
Reddit Scraper (Apify Edition) — Pulls Google Photos search-failure complaints from Reddit.

Sources: r/googlephotos, r/Android, r/photography, r/google, r/pixel_phones
Uses: ApifyClientAsync with 'trudax/reddit-scraper-lite' Actor
Target: 3,000–4,000 records
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

try:
    from apify_client import ApifyClientAsync
except ImportError:
    ApifyClientAsync = None
    logger.warning("apify-client not installed. Install with: pip install apify-client")

from ingestion.base_scraper import BaseScraper


class RedditScraper(BaseScraper):
    """Scrape Google Photos search-failure complaints from Reddit using Apify."""

    MAX_CONCURRENT_REQUESTS = 1  # Apify runs the heavy lifting; we just orchestrate
    
    # Subreddits to search
    SUBREDDITS = [
        "googlephotos",
        "Android",
        "photography",
        "google",
        "pixel_phones",
        "GooglePixel",
        "ios",
        "iphone",
    ]

    # Search queries — each targets a different failure mode
    SEARCH_QUERIES = [
        "google photos can't find",
        "google photos search not working",
        "google photos lost photo",
        "google photos missing photo",
        "google photos remember photo",
        "google photos search broken",
        "google photos find old photo",
        "google photos search results wrong",
        "can't find photo google",
        "google photos scroll forever",
        "google photos search useless",
        "photo disappeared google",
        "find picture google photos",
        "google photos search tips",
        "google photos where is my photo",
    ]

    # Keywords to filter relevant content locally
    RELEVANCE_KEYWORDS = [
        "find", "search", "lost", "missing", "remember", "looking for",
        "can't find", "cannot find", "couldn't find", "where is",
        "disappeared", "gone", "scroll", "browse", "retrieve",
        "photo", "picture", "image", "video", "screenshot",
    ]

    @property
    def source_name(self) -> str:
        return "reddit"

    def __init__(self, output_dir: str = None):
        super().__init__(output_dir)
        self._apify_token = os.getenv("APIFY_TOKEN")
        self._client = None
        if self._apify_token:
            self._client = ApifyClientAsync(self._apify_token)

    async def scrape(self):
        """
        Main scrape generator. Constructs search URLs for Apify, runs the Actor,
        and yields relevant results.
        """
        if not self._client:
            logger.error("[reddit] APIFY_TOKEN is missing or apify-client is not installed.")
            return

        # Load checkpoint if resuming
        checkpoint = self.load_checkpoint()
        completed_batches = set()
        if checkpoint:
            completed_batches = set(checkpoint.get("completed_batches", []))

        # We will batch queries to send to Apify so we don't start 100 separate runs.
        # Let's chunk the search URLs into batches of 10.
        all_urls = []
        for subreddit in self.SUBREDDITS:
            for query in self.SEARCH_QUERIES:
                encoded_query = quote_plus(query)
                # Construct Reddit search URL
                search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={encoded_query}&restrict_sr=1"
                all_urls.append(search_url)

        batch_size = 10
        url_batches = [all_urls[i:i + batch_size] for i in range(0, len(all_urls), batch_size)]

        for i, batch in enumerate(url_batches):
            batch_id = f"batch_{i}"
            if batch_id in completed_batches:
                logger.debug(f"[reddit] Skipping completed batch {i+1}/{len(url_batches)}")
                continue

            logger.info(f"[reddit] Running Apify scraper for batch {i+1}/{len(url_batches)} ({len(batch)} URLs)")

            start_urls = [{"url": url} for url in batch]
            
            run_input = {
                "startUrls": start_urls,
                "maxItems": 1000, # Per run cap
                "sort": "new",
            }

            try:
                # Call the actor
                run = await self._client.actor("trudax/reddit-scraper-lite").call(run_input=run_input)
                
                if hasattr(run, "default_dataset_id"):
                    dataset_id = run.default_dataset_id
                elif hasattr(run, "get"):
                    dataset_id = run.get("defaultDatasetId")
                else:
                    dataset_id = run["defaultDatasetId"]
                
                # Fetch dataset items
                dataset = self._client.dataset(dataset_id)
                items = (await dataset.list_items()).items
                
                logger.info(f"[reddit] Apify batch {i+1} completed. Fetched {len(items)} items.")

                for item in items:
                    title = item.get("title", "")
                    body = item.get("text", "") or item.get("content", "") or item.get("body", "")
                    url = item.get("url", "")
                    
                    full_text = f"{title}\n\n{body}".strip()

                    # Apply relevance filtering locally just in case
                    if full_text and self.keyword_match(full_text, self.RELEVANCE_KEYWORDS):
                        yield {
                            "raw_text": full_text,
                            "url_id": url or f"reddit_apify_{item.get('id', hash(full_text))}",
                            "metadata": {
                                "subreddit": item.get("subreddit", ""),
                                "score": item.get("upvotes", 0) or item.get("score", 0),
                                "author": item.get("author", ""),
                                "created_utc": item.get("createdAt", ""),
                                "type": "submission",
                                "via": "apify",
                            },
                        }
                
                # Update checkpoint
                completed_batches.add(batch_id)
                self.save_checkpoint({
                    "completed_batches": list(completed_batches)
                })

            except Exception as e:
                logger.warning(f"[reddit] Error running Apify for batch {i+1}: {e}")
                # We save checkpoint without this batch to retry later
                self.save_checkpoint({
                    "completed_batches": list(completed_batches),
                    "error": str(e)
                })
                # Back off slightly before next batch
                await asyncio.sleep(5)
