"""
Base Scraper — Abstract async scraper with production-grade features.

Provides:
  - asyncio.Semaphore rate limiting
  - Exponential backoff with jitter (base=1s, max=60s)
  - .jsonl append-only writer (partitioned by date + batch)
  - Cursor-based checkpoint/resume
  - SHA-256 content deduplication
"""

import abc
import asyncio
import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseScraper(abc.ABC):
    """
    Abstract base class for all data scrapers.

    Subclasses must implement:
      - source_name (property): e.g. "reddit", "appstore"
      - scrape() -> AsyncGenerator: yields raw record dicts
    """

    # --- Configuration ---
    MAX_CONCURRENT_REQUESTS: int = 2
    BACKOFF_BASE: float = 1.0
    BACKOFF_MAX: float = 60.0
    BACKOFF_FACTOR: float = 2.0
    MAX_RETRIES: int = 5
    BATCH_SIZE: int = 500  # Records per .jsonl file
    MIN_TEXT_LENGTH: int = 20  # Skip texts shorter than this

    def __init__(self, output_dir: str = None):
        """
        Initialize the base scraper.

        Args:
            output_dir: Root directory for raw data output.
                        Defaults to backend/data/raw/{source_name}/
        """
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        self._seen_hashes: set[str] = set()
        self._records_scraped: int = 0
        self._records_skipped_short: int = 0
        self._records_skipped_dup: int = 0
        self._start_time: float = 0
        self._checkpoint: dict = {}

        # Output directory
        if output_dir:
            self._output_dir = Path(output_dir)
        else:
            base = Path(__file__).parent.parent / "data" / "raw"
            self._output_dir = base / self.source_name

        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Checkpoint file
        self._checkpoint_file = self._output_dir / ".checkpoint.json"

    # --- Abstract Interface ---

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Return the source platform name (e.g., 'reddit', 'appstore')."""
        ...

    @abc.abstractmethod
    async def scrape(self):
        """
        Async generator that yields raw record dicts.

        Each yielded dict must have:
          - "raw_text": str
          - "url_id": str (unique identifier for this record)
          - "metadata": dict (source-specific metadata)
        """
        ...

    # --- Rate Limiting & Backoff ---

    async def rate_limited_request(self, coro_func, *args, **kwargs):
        """
        Execute an async function with semaphore-based rate limiting
        and exponential backoff on failure.

        Args:
            coro_func: Async function to call
            *args, **kwargs: Arguments to pass to the function

        Returns:
            The result of coro_func(*args, **kwargs)

        Raises:
            Exception: If all retries are exhausted
        """
        async with self._semaphore:
            delay = self.BACKOFF_BASE
            last_exception = None

            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    result = await coro_func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt == self.MAX_RETRIES:
                        logger.error(
                            f"[{self.source_name}] All {self.MAX_RETRIES} retries exhausted: {e}"
                        )
                        raise

                    # Add jitter: delay * (0.5 to 1.5)
                    jittered_delay = delay * (0.5 + random.random())
                    logger.warning(
                        f"[{self.source_name}] Attempt {attempt}/{self.MAX_RETRIES} failed: {e}. "
                        f"Retrying in {jittered_delay:.1f}s..."
                    )
                    await asyncio.sleep(jittered_delay)
                    delay = min(delay * self.BACKOFF_FACTOR, self.BACKOFF_MAX)

            raise last_exception  # Should not reach here

    # --- Deduplication ---

    def _content_hash(self, text: str) -> str:
        """Generate SHA-256 hash of normalized text for deduplication."""
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_duplicate(self, text: str) -> bool:
        """Check if text has already been seen (dedup via SHA-256 hash set)."""
        h = self._content_hash(text)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False

    # --- Text Validation ---

    def is_valid_text(self, text: str) -> bool:
        """
        Check if text meets minimum quality requirements.

        Returns False for:
          - None or empty strings
          - Text shorter than MIN_TEXT_LENGTH
          - Text with fewer than 3 alphanumeric words
        """
        if not text or not isinstance(text, str):
            return False

        stripped = text.strip()
        if len(stripped) < self.MIN_TEXT_LENGTH:
            return False

        # Count alphanumeric words
        import re
        words = re.findall(r"[a-zA-Z0-9]+", stripped)
        if len(words) < 3:
            return False

        return True

    def clean_text(self, text: str) -> str:
        """Clean and normalize raw text."""
        if not text:
            return ""

        from bs4 import BeautifulSoup

        # Strip HTML tags
        try:
            text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
        except Exception:
            pass

        # Normalize whitespace
        text = " ".join(text.split())

        # Truncate extremely long texts (> 10,000 chars)
        if len(text) > 10000:
            text = text[:10000] + "..."

        return text.strip()

    # --- Checkpoint / Resume ---

    def save_checkpoint(self, cursor_data: dict):
        """Save checkpoint cursor to disk for resume capability."""
        self._checkpoint = {
            "source": self.source_name,
            "cursor": cursor_data,
            "records_scraped": self._records_scraped,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self._checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(self._checkpoint, f, indent=2)
            logger.debug(f"[{self.source_name}] Checkpoint saved: {self._records_scraped} records")
        except Exception as e:
            logger.warning(f"[{self.source_name}] Failed to save checkpoint: {e}")

    def load_checkpoint(self) -> dict | None:
        """Load checkpoint cursor from disk. Returns None if no checkpoint exists."""
        if not self._checkpoint_file.exists():
            return None
        try:
            with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(
                f"[{self.source_name}] Resuming from checkpoint: "
                f"{data.get('records_scraped', 0)} records previously scraped"
            )
            return data.get("cursor")
        except Exception as e:
            logger.warning(f"[{self.source_name}] Failed to load checkpoint: {e}")
            return None

    def clear_checkpoint(self):
        """Remove checkpoint file after successful completion."""
        if self._checkpoint_file.exists():
            self._checkpoint_file.unlink()
            logger.debug(f"[{self.source_name}] Checkpoint cleared")

    # --- JSONL Writer ---

    def _get_output_path(self, batch_num: int) -> Path:
        """Generate output file path: data/raw/{source}/{date}/batch_{N}.jsonl"""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = self._output_dir / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        return day_dir / f"batch_{batch_num:04d}.jsonl"

    def _write_batch(self, records: list[dict], batch_num: int) -> str:
        """Write a batch of records to a .jsonl file. Returns the file path."""
        path = self._get_output_path(batch_num)
        with open(path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(
            f"[{self.source_name}] Wrote {len(records)} records to {path.name}"
        )
        return str(path)

    # --- Main Run Method ---

    async def run(self, max_records: int = None) -> dict:
        """
        Execute the scraper end-to-end.

        Args:
            max_records: Optional cap on total records to scrape.

        Returns:
            dict with scraping statistics:
              - source: str
              - records_scraped: int
              - records_skipped_short: int
              - records_skipped_dup: int
              - batches_written: int
              - output_files: list[str]
              - duration_seconds: float
        """
        self._start_time = time.time()
        self._records_scraped = 0
        self._records_skipped_short = 0
        self._records_skipped_dup = 0

        current_batch: list[dict] = []
        batch_num = 0
        output_files: list[str] = []

        logger.info(f"[{self.source_name}] Starting scraper (max_records={max_records})")

        try:
            async for record in self.scrape():
                raw_text = record.get("raw_text", "")

                # Clean the text
                cleaned = self.clean_text(raw_text)

                # Validate
                if not self.is_valid_text(cleaned):
                    self._records_skipped_short += 1
                    continue

                # Dedup
                if self.is_duplicate(cleaned):
                    self._records_skipped_dup += 1
                    continue

                # Build the standardized record
                standardized = {
                    "source_platform": self.source_name,
                    "url_id": record.get("url_id", ""),
                    "raw_text": cleaned,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": record.get("metadata", {}),
                }

                current_batch.append(standardized)
                self._records_scraped += 1

                # Write batch when full
                if len(current_batch) >= self.BATCH_SIZE:
                    path = self._write_batch(current_batch, batch_num)
                    output_files.append(path)
                    current_batch = []
                    batch_num += 1

                    # Save checkpoint every batch
                    self.save_checkpoint({"batch_num": batch_num, "total": self._records_scraped})

                # Check cap
                if max_records and self._records_scraped >= max_records:
                    logger.info(
                        f"[{self.source_name}] Reached max_records cap ({max_records})"
                    )
                    break

                # Log progress every 500 records
                if self._records_scraped % 500 == 0 and self._records_scraped > 0:
                    elapsed = time.time() - self._start_time
                    rate = self._records_scraped / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"[{self.source_name}] Progress: {self._records_scraped} records "
                        f"({rate:.1f} rec/s) | "
                        f"skipped: {self._records_skipped_short} short, "
                        f"{self._records_skipped_dup} dupes"
                    )

            # Write remaining records
            if current_batch:
                path = self._write_batch(current_batch, batch_num)
                output_files.append(path)
                batch_num += 1

        except Exception as e:
            logger.error(f"[{self.source_name}] Scraper failed: {e}")
            # Save checkpoint on failure for resume
            self.save_checkpoint({
                "batch_num": batch_num,
                "total": self._records_scraped,
                "error": str(e),
            })
            raise
        finally:
            # Clear checkpoint on successful completion
            if self._records_scraped > 0:
                self.clear_checkpoint()

        elapsed = time.time() - self._start_time
        stats = {
            "source": self.source_name,
            "records_scraped": self._records_scraped,
            "records_skipped_short": self._records_skipped_short,
            "records_skipped_dup": self._records_skipped_dup,
            "batches_written": batch_num,
            "output_files": output_files,
            "duration_seconds": round(elapsed, 1),
        }

        logger.info(
            f"[{self.source_name}] Complete: {self._records_scraped} records in {elapsed:.1f}s "
            f"({batch_num} batches) | "
            f"Skipped: {self._records_skipped_short} short, {self._records_skipped_dup} dupes"
        )

        return stats

    # --- Utility ---

    @staticmethod
    def keyword_match(text: str, keywords: list[str]) -> bool:
        """Check if text contains any of the given keywords (case-insensitive)."""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    @property
    def stats(self) -> dict:
        """Return current scraping statistics."""
        return {
            "source": self.source_name,
            "records_scraped": self._records_scraped,
            "records_skipped_short": self._records_skipped_short,
            "records_skipped_dup": self._records_skipped_dup,
            "unique_hashes": len(self._seen_hashes),
        }
