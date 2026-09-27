"""
Help Forum Scraper — Pulls complaints from Google Photos Help Community.

Source: https://support.google.com/photos/community (Google Support Forums)
Uses: aiohttp + BeautifulSoup, with Playwright fallback for JS-rendered pages
Target: 2,000–3,000 records
"""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlencode, quote_plus

logger = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from ingestion.base_scraper import BaseScraper


# User-Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
]

# Base URLs
GOOGLE_SUPPORT_BASE = "https://support.google.com"
PHOTOS_COMMUNITY_BASE = f"{GOOGLE_SUPPORT_BASE}/photos/community"


class HelpForumScraper(BaseScraper):
    """Scrape Google Photos Help Community forum threads."""

    MAX_CONCURRENT_REQUESTS = 2
    BATCH_SIZE = 500

    # Search queries for the Google Help Community
    SEARCH_QUERIES = [
        "can't find photo",
        "search not working",
        "photos missing",
        "photo disappeared",
        "lost photos",
        "search returns nothing",
        "where are my photos",
        "old photos gone",
        "cannot find picture",
        "search broken",
        "photo search",
        "find old photo",
        "remember photo can't find",
        "scroll through photos",
        "photos not showing",
    ]

    # Keywords for relevance filtering
    RELEVANCE_KEYWORDS = [
        "find", "search", "lost", "missing", "remember", "looking for",
        "can't find", "cannot find", "couldn't find", "where is",
        "disappeared", "gone", "scroll", "retrieve", "not showing",
        "won't show", "doesn't show", "not appearing",
    ]

    @property
    def source_name(self) -> str:
        return "helpforum"

    async def scrape(self):
        """Main scrape generator — searches Google Help Community and extracts threads."""
        if aiohttp is None:
            logger.error("[helpforum] aiohttp not installed")
            return

        # Strategy 1: Use Google Search to find relevant support threads
        async for record in self._scrape_via_google_search():
            yield record

        # Strategy 2: Direct community URL crawling
        async for record in self._scrape_community_direct():
            yield record

    # ─── Strategy 1: Google Search for Support Threads ─────────────

    async def _scrape_via_google_search(self):
        """
        Use Google Search to find Google Photos support threads about search failures.
        Queries: site:support.google.com/photos "can't find" OR "search" OR "missing"
        """
        logger.info("[helpforum] Starting Google Search-based scrape...")

        async with aiohttp.ClientSession() as session:
            for query in self.SEARCH_QUERIES:
                search_query = f'site:support.google.com/photos/thread "{query}"'

                try:
                    async for record in self._google_search(session, search_query):
                        yield record
                except Exception as e:
                    logger.warning(f"[helpforum] Google search error for '{query}': {e}")

                # Delay between searches
                await asyncio.sleep(random.uniform(3.0, 6.0))

    async def _google_search(self, session: "aiohttp.ClientSession", query: str, num_results: int = 50):
        """
        Perform a Google search and extract support thread URLs.
        Then fetch each thread to extract content.
        """
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        # Use Google's search with a simple HTML scrape
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"

        try:
            async with session.get(
                search_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"[helpforum] Google search returned {resp.status}")
                    return

                html = await resp.text()

            if not BeautifulSoup:
                return

            soup = BeautifulSoup(html, "html.parser")

            # Extract URLs from search results
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                # Look for Google Support thread URLs
                if "support.google.com/photos/thread" in href:
                    # Clean the URL
                    clean_url = href
                    if "/url?q=" in href:
                        clean_url = href.split("/url?q=")[1].split("&")[0]
                    links.append(clean_url)

            logger.info(f"[helpforum] Found {len(links)} support thread URLs")

            # Fetch each thread
            for url in links[:30]:  # Cap at 30 per search to avoid rate limits
                async for record in self._fetch_thread(session, url):
                    yield record
                await asyncio.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            logger.warning(f"[helpforum] Google search failed: {e}")

    async def _fetch_thread(self, session: "aiohttp.ClientSession", url: str):
        """Fetch a single support forum thread and extract posts."""
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return
                html = await resp.text()

            if not BeautifulSoup:
                return

            soup = BeautifulSoup(html, "html.parser")

            # Extract the main question / thread body
            # Google Support forums have varying HTML structures
            # Try multiple selectors
            content_selectors = [
                "div.thread-question",
                "div.question-body",
                "div[class*='question']",
                "div.thread-message",
                "article",
                "div.post-content",
                "div[class*='content']",
            ]

            texts_found = []

            for selector in content_selectors:
                elements = soup.select(selector)
                for el in elements:
                    text = el.get_text(separator=" ", strip=True)
                    if text and len(text) > 30:
                        texts_found.append(text)

            # Fallback: extract all paragraph text from the page
            if not texts_found:
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 50 and self.keyword_match(text, self.RELEVANCE_KEYWORDS):
                        texts_found.append(text)

            # Also extract reply content
            reply_selectors = [
                "div.thread-reply",
                "div.reply-body",
                "div[class*='reply']",
                "div.community-reply",
            ]

            for selector in reply_selectors:
                elements = soup.select(selector)
                for el in elements:
                    text = el.get_text(separator=" ", strip=True)
                    if text and len(text) > 30 and self.keyword_match(text, self.RELEVANCE_KEYWORDS):
                        texts_found.append(text)

            # Deduplicate within this thread
            seen = set()
            for text in texts_found:
                normalized = text[:200]  # Use first 200 chars as key
                if normalized not in seen:
                    seen.add(normalized)
                    yield {
                        "raw_text": text,
                        "url_id": f"{url}#post_{hash(normalized) % 100000}",
                        "metadata": {
                            "forum": "google_photos_help",
                            "thread_url": url,
                            "type": "forum_post",
                        },
                    }

        except asyncio.TimeoutError:
            logger.warning(f"[helpforum] Timeout fetching: {url}")
        except Exception as e:
            logger.warning(f"[helpforum] Error fetching {url}: {e}")

    # ─── Strategy 2: Direct Community Crawl ─────────────────────────

    async def _scrape_community_direct(self):
        """
        Directly crawl the Google Photos Help Community pages.
        This is a supplementary approach that targets the community listing pages.
        """
        logger.info("[helpforum] Starting direct community crawl...")

        base_urls = [
            "https://support.google.com/photos/community?hl=en",
            "https://support.google.com/photos/community?hl=en&filter=search",
        ]

        async with aiohttp.ClientSession() as session:
            for base_url in base_urls:
                try:
                    async for record in self._crawl_listing_page(session, base_url):
                        yield record
                except Exception as e:
                    logger.warning(f"[helpforum] Error crawling {base_url}: {e}")

                await asyncio.sleep(random.uniform(2.0, 4.0))

    async def _crawl_listing_page(self, session, url: str, max_pages: int = 20):
        """Crawl a community listing page and follow thread links."""
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        for page in range(max_pages):
            page_url = f"{url}&page={page + 1}" if page > 0 else url

            try:
                async with session.get(
                    page_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        break
                    html = await resp.text()

                if not BeautifulSoup:
                    return

                soup = BeautifulSoup(html, "html.parser")

                # Find thread links
                thread_links = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "/thread/" in href:
                        full_url = urljoin(GOOGLE_SUPPORT_BASE, href)
                        thread_links.append(full_url)

                if not thread_links:
                    break

                logger.info(
                    f"[helpforum] Community page {page + 1}: found {len(thread_links)} threads"
                )

                # Fetch each thread
                for thread_url in thread_links:
                    async for record in self._fetch_thread(session, thread_url):
                        yield record
                    await asyncio.sleep(random.uniform(1.0, 2.5))

            except Exception as e:
                logger.warning(f"[helpforum] Error on listing page {page + 1}: {e}")
                break

            await asyncio.sleep(random.uniform(2.0, 4.0))

    # ─── Playwright Fallback ─────────────────────────────────────────

    async def scrape_with_playwright(self, urls: list[str] = None):
        """
        Fallback scraper using Playwright for JS-rendered pages.
        Use when aiohttp+BeautifulSoup can't extract content.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("[helpforum] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return

        urls = urls or [
            f"https://support.google.com/photos/community?hl=en",
        ]

        logger.info(f"[helpforum] Starting Playwright scrape for {len(urls)} URLs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=random.choice(USER_AGENTS))

            for url in urls:
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(2)

                    # Extract all text content from thread-like elements
                    content_elements = await page.query_selector_all(
                        "div[class*='thread'], div[class*='question'], div[class*='post'], article"
                    )

                    for element in content_elements:
                        text = await element.inner_text()
                        if text and len(text) > 30 and self.keyword_match(text, self.RELEVANCE_KEYWORDS):
                            yield {
                                "raw_text": text,
                                "url_id": f"{url}#pw_{hash(text[:200]) % 100000}",
                                "metadata": {
                                    "forum": "google_photos_help",
                                    "thread_url": url,
                                    "type": "playwright_extracted",
                                },
                            }

                except Exception as e:
                    logger.warning(f"[helpforum] Playwright error for {url}: {e}")

                await asyncio.sleep(random.uniform(2.0, 4.0))

            await browser.close()
