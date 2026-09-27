"""
Ingestion Orchestrator — Runs all 4 scrapers concurrently.

Usage:
  python -m ingestion.run_ingestion                    # Run all scrapers
  python -m ingestion.run_ingestion --source reddit    # Run a specific scraper
  python -m ingestion.run_ingestion --max 1000         # Cap records per source
  python -m ingestion.run_ingestion --dry-run          # Test without writing

Outputs:
  - .jsonl files in data/raw/{source}/{date}/batch_XXXX.jsonl
  - Ingestion statistics logged to console
  - Checkpoint files for resume capability
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from ingestion.reddit_scraper import RedditScraper
from ingestion.appstore_scraper import AppStoreScraper
from ingestion.helpforum_scraper import HelpForumScraper
from ingestion.youtube_scraper import YouTubeScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent.parent / "data" / "ingestion.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)


# --- Scraper Registry ---
SCRAPERS = {
    "reddit": RedditScraper,
    "appstore": AppStoreScraper,
    "helpforum": HelpForumScraper,
    "youtube": YouTubeScraper,
}

# Target volumes per source (scaled to achieve 10,000+ total records)
TARGET_VOLUMES = {
    "reddit": 3000,
    "appstore": 8000,
    "helpforum": 1000,
    "youtube": 3000,
}


async def run_single_scraper(
    name: str,
    scraper_class,
    max_records: int = None,
) -> dict:
    """
    Run a single scraper and return its statistics.

    Args:
        name: Scraper name (for logging)
        scraper_class: The scraper class to instantiate
        max_records: Optional cap on records

    Returns:
        dict with scraper statistics
    """
    logger.info(f"{'='*60}")
    logger.info(f"  Starting {name} scraper (max_records={max_records})")
    logger.info(f"{'='*60}")

    try:
        scraper = scraper_class()
        stats = await scraper.run(max_records=max_records)
        logger.info(f"  ✅ {name}: {stats['records_scraped']} records scraped")
        return stats
    except Exception as e:
        logger.error(f"  ❌ {name}: Failed with error: {e}")
        return {
            "source": name,
            "records_scraped": 0,
            "error": str(e),
            "duration_seconds": 0,
        }


async def run_all_scrapers(
    sources: list[str] = None,
    max_records_per_source: int = None,
    sequential: bool = False,
) -> dict:
    """
    Run all (or selected) scrapers and aggregate results.

    Args:
        sources: List of source names to run. None = all.
        max_records_per_source: Cap per scraper. None = use TARGET_VOLUMES.
        sequential: If True, run scrapers one at a time (easier to debug).

    Returns:
        dict with aggregated statistics
    """
    sources_to_run = sources or list(SCRAPERS.keys())
    start_time = time.time()

    logger.info("🚀 Google Photos Discovery Engine — Ingestion Pipeline")
    logger.info(f"   Sources: {', '.join(sources_to_run)}")
    logger.info(f"   Max records per source: {max_records_per_source or 'target-based'}")
    logger.info(f"   Mode: {'sequential' if sequential else 'concurrent'}")
    logger.info("")

    all_stats = []

    if sequential:
        # Run one at a time (useful for debugging)
        for name in sources_to_run:
            if name not in SCRAPERS:
                logger.warning(f"   Unknown source: {name}. Skipping.")
                continue
            cap = max_records_per_source or TARGET_VOLUMES.get(name, 5000)
            stats = await run_single_scraper(name, SCRAPERS[name], max_records=cap)
            all_stats.append(stats)
    else:
        # Run all concurrently
        tasks = []
        for name in sources_to_run:
            if name not in SCRAPERS:
                logger.warning(f"   Unknown source: {name}. Skipping.")
                continue
            cap = max_records_per_source or TARGET_VOLUMES.get(name, 5000)
            tasks.append(run_single_scraper(name, SCRAPERS[name], max_records=cap))

        all_stats = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # Aggregate results
    total_records = sum(s.get("records_scraped", 0) for s in all_stats)
    total_skipped_short = sum(s.get("records_skipped_short", 0) for s in all_stats)
    total_skipped_dup = sum(s.get("records_skipped_dup", 0) for s in all_stats)
    total_batches = sum(s.get("batches_written", 0) for s in all_stats)
    errors = [s for s in all_stats if "error" in s]

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  INGESTION PIPELINE RESULTS")
    logger.info("=" * 60)
    for s in all_stats:
        icon = "✅" if s.get("records_scraped", 0) > 0 else "❌"
        logger.info(
            f"  {icon} {s['source']:12s}: {s.get('records_scraped', 0):>6,} records "
            f"({s.get('duration_seconds', 0):.0f}s)"
        )
    logger.info("-" * 60)
    logger.info(f"  📊 Total records:    {total_records:>6,}")
    logger.info(f"  📊 Skipped (short):  {total_skipped_short:>6,}")
    logger.info(f"  📊 Skipped (dupes):  {total_skipped_dup:>6,}")
    logger.info(f"  📊 Batches written:  {total_batches:>6}")
    logger.info(f"  ⏱️  Total time:       {elapsed:.1f}s ({elapsed/60:.1f}m)")
    if errors:
        logger.info(f"  ⚠️  Errors:           {len(errors)}")
    logger.info("=" * 60)

    # Volume check
    if total_records >= 10000:
        logger.info("  🎉 Target volume (10,000+) ACHIEVED!")
    else:
        shortfall = 10000 - total_records
        logger.warning(
            f"  ⚠️  Below target: {total_records} / 10,000 (short by {shortfall}). "
            f"Consider broadening keywords or adding supplementary sources."
        )

    # Save summary to file
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_records": total_records,
        "total_skipped_short": total_skipped_short,
        "total_skipped_dup": total_skipped_dup,
        "total_batches": total_batches,
        "duration_seconds": round(elapsed, 1),
        "per_source": all_stats,
    }

    summary_path = Path(__file__).parent.parent / "data" / "ingestion_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info(f"  📄 Summary saved to: {summary_path}")

    return summary


# --- Count Existing Records ---

def count_existing_records() -> dict:
    """Count .jsonl records already in data/raw/ (for resume awareness)."""
    data_dir = Path(__file__).parent.parent / "data" / "raw"
    counts = {}

    if not data_dir.exists():
        return counts

    for source_dir in data_dir.iterdir():
        if source_dir.is_dir() and source_dir.name != ".gitkeep":
            count = 0
            for jsonl_file in source_dir.rglob("*.jsonl"):
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    count += sum(1 for line in f if line.strip())
            counts[source_dir.name] = count

    return counts


# --- CLI Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="Google Photos Discovery Engine — Data Ingestion Pipeline"
    )
    parser.add_argument(
        "--source",
        choices=list(SCRAPERS.keys()),
        nargs="+",
        help="Run specific scraper(s). Default: all.",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Max records per source. Default: use target volumes.",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run scrapers one at a time (easier to debug).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without writing files.",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Count existing records and exit.",
    )

    args = parser.parse_args()

    if args.count:
        counts = count_existing_records()
        total = sum(counts.values())
        print(f"\n[STATS] Existing records in data/raw/:")
        for source, count in sorted(counts.items()):
            print(f"   {source:12s}: {count:>6,}")
        print(f"   {'TOTAL':12s}: {total:>6,}")
        print()
        return

    if args.dry_run:
        print("\n[DRY RUN] Would scrape from:")
        sources = args.source or list(SCRAPERS.keys())
        for name in sources:
            cap = args.max or TARGET_VOLUMES.get(name, 5000)
            print(f"   {name:12s}: up to {cap:>6,} records")
        print()
        return

    # Run the ingestion pipeline
    asyncio.run(
        run_all_scrapers(
            sources=args.source,
            max_records_per_source=args.max,
            sequential=args.sequential,
        )
    )


if __name__ == "__main__":
    main()
