"""
End-to-End Pipeline Orchestrator

Runs all pipeline phases in sequence:
  Phase 1: Ingestion   — Scrape 10,000+ complaints
  Phase 2: Extraction  — Gemini Batch API structured extraction
  Phase 3: Embedding   — Generate text-embedding-004 vectors
  Phase 4: Clustering  — HDBSCAN clustering + metrics
  Phase 5: Synthesis   — AI-generated answers to 5 core questions

Usage:
  python scripts/run_pipeline.py                  # Run all phases
  python scripts/run_pipeline.py --phase 1        # Run a specific phase
  python scripts/run_pipeline.py --phase 3 --to 5 # Run phases 3 through 5
"""

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def run_phase_1_ingestion():
    """Phase 1: Run all scrapers to collect raw user complaints."""
    print("\n📥 Phase 1: Data Ingestion")
    print("   Scraping Reddit, App Stores, Help Forum, YouTube...")
    from ingestion.run_ingestion import run_all_scrapers
    await run_all_scrapers()

async def run_phase_2_extraction():
    """Phase 2: Extract structured data from raw complaints using Gemini."""
    print("\n🔬 Phase 2: Gemini Extraction")
    print("   Processing raw text through Gemini Batch API...")
    from scripts.run_extraction import run_extraction
    await run_extraction()

async def run_phase_3_embedding():
    """Phase 3: Generate vector embeddings for all records."""
    print("\n🧮 Phase 3: Embedding Generation")
    print("   Generating text-embedding-004 vectors...")
    from scripts.run_clustering import run_embedding_phase
    from db.connection import get_pool
    pool = await get_pool()
    await run_embedding_phase(pool)

async def run_phase_4_clustering():
    """Phase 4: Cluster embeddings and compute metrics."""
    print("\n🔮 Phase 4: Clustering & Metrics")
    print("   Running UMAP + HDBSCAN clustering pipeline...")
    from scripts.run_clustering import run_clustering_phase
    from db.connection import get_pool
    pool = await get_pool()
    await run_clustering_phase(pool)

async def run_phase_5_synthesis():
    """Phase 5: Generate AI-synthesized answers to core questions."""
    print("\n🧠 Phase 5: AI Synthesis")
    print("   Generating evidence-backed answers to 5 core questions...")
    from scripts.run_synthesis import run_synthesis_pipeline
    await run_synthesis_pipeline()


PHASES = {
    1: ("Ingestion", run_phase_1_ingestion),
    2: ("Extraction", run_phase_2_extraction),
    3: ("Embedding", run_phase_3_embedding),
    4: ("Clustering", run_phase_4_clustering),
    5: ("Synthesis", run_phase_5_synthesis),
}


async def main():
    parser = argparse.ArgumentParser(description="Discovery Engine Pipeline Orchestrator")
    parser.add_argument("--phase", type=int, help="Run a specific phase (1-5)")
    parser.add_argument("--to", type=int, help="Run phases from --phase to --to (inclusive)")
    args = parser.parse_args()

    print("🚀 Google Photos Discovery Engine — Pipeline Orchestrator")
    print("=" * 60)

    if args.phase:
        start = args.phase
        end = args.to or args.phase
    else:
        start, end = 1, 5

    for phase_num in range(start, end + 1):
        if phase_num not in PHASES:
            print(f"\n❌ Unknown phase: {phase_num}")
            continue

        name, func = PHASES[phase_num]
        t0 = time.time()
        try:
            await func()
            elapsed = time.time() - t0
            print(f"   ✅ Phase {phase_num} ({name}) completed in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"   ❌ Phase {phase_num} ({name}) failed after {elapsed:.1f}s: {e}")
            print(f"   ⚠️  Stopping pipeline. Fix the error and re-run from phase {phase_num}.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("🏁 Pipeline complete!")


if __name__ == "__main__":
    asyncio.run(main())
