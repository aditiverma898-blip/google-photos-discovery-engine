import os
import sys
import json
import asyncio
import logging
import argparse
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extraction.batch_processor import process_raw_data
from extraction.validator import validate_and_filter_records
from db.connection import get_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def get_existing_url_ids() -> set[str]:
    """Fetch all url_ids already in the feedback_records table."""
    conn = await get_pool()
    async with conn.execute("SELECT url_id FROM feedback_records") as cursor:
        rows = await cursor.fetchall()
        return {r[0] for r in rows}

async def insert_into_db(valid_records: list[dict]):
    """Bulk inserts valid records into SQLite."""
    conn = await get_pool()
    
    insert_query = """
    INSERT INTO feedback_records (
        source_platform, url_id, raw_text, photo_type, 
        remembered_attributes, forgotten_attributes, 
        search_strategy, failure_point, workaround, emotional_signal
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT (url_id) DO NOTHING
    """
    
    records_to_insert = []
    for r in valid_records:
        records_to_insert.append((
            r['source_platform'],
            r['url_id'],
            r['raw_text'],
            r['photo_type'],
            json.dumps(r['remembered_attributes']),
            json.dumps(r['forgotten_attributes']),
            r['search_strategy'],
            r['failure_point'],
            r.get('workaround', ''),
            r['emotional_signal']
        ))
        
    logger.info(f"Inserting {len(records_to_insert)} records into database...")
    await conn.executemany(insert_query, records_to_insert)
    await conn.commit()
    logger.info("Database insertion complete.")

async def run_extraction(limit: int = 100):
    raw_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    
    if not os.path.exists(raw_data_dir):
        logger.error(f"Raw data directory {raw_data_dir} does not exist.")
        return

    logger.info(f"Starting Extraction Pipeline (limit={limit})...")
    
    # Step 0: Check existing records in DB
    existing_ids = await get_existing_url_ids()
    logger.info(f"Found {len(existing_ids)} records already present in database.")

    # Step 1: Read and Extract with Gemini
    raw_responses = await process_raw_data(raw_data_dir, limit=limit, existing_ids=existing_ids)
    
    if not raw_responses:
        logger.info("No new records to extract.")
        return
        
    # Step 2: Validate & Filter
    valid_records = validate_and_filter_records(raw_responses)
    
    # Step 3: Insert into DB
    if valid_records:
        await insert_into_db(valid_records)
    else:
        logger.warning("No valid records found to insert.")

    # Step 4: Final DB count check
    conn = await get_pool()
    async with conn.execute("SELECT count(*) FROM feedback_records") as cursor:
        cnt = (await cursor.fetchone())[0]
        logger.info(f"Total feedback_records in database now: {cnt}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2: Extraction Pipeline")
    parser.add_argument("--limit", type=int, default=100, help="Max number of records to extract in this run")
    args = parser.parse_args()

    asyncio.run(run_extraction(limit=args.limit))
