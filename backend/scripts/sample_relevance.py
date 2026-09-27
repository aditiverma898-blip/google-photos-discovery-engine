import os
import sqlite3
import json
import time
import argparse
import logging
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=API_KEY)

class RelevanceCheck(BaseModel):
    id: int = Field(description="The ID of the record")
    is_retrieval_relevant: bool = Field(description="True if the user is explicitly describing a failed attempt to search for, retrieve, or locate a specific photo/album.")

class BatchRelevanceCheck(BaseModel):
    results: list[RelevanceCheck]

def setup_sample(db):
    logger.info("Setting up stratified sample...")
    db.execute("UPDATE feedback_records SET is_sample_target = 0")
    
    # Process all of Cluster 0
    db.execute("UPDATE feedback_records SET is_sample_target = 1 WHERE cluster_id = 0")
    
    # Process all of Clusters 1-5 (removed artificial 2500 cap)
    db.execute("UPDATE feedback_records SET is_sample_target = 1 WHERE cluster_id BETWEEN 1 AND 5")
    
    db.commit()
    target_count = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_sample_target = 1").fetchone()[0]
    logger.info(f"Sample setup complete. Total target records: {target_count}")

def process_batch(batch):
    prompt = """Evaluate the following user feedback records from Google Photos. Determine if each record is a genuine photo retrieval/search failure.
    
A record is a VALID retrieval failure (is_retrieval_relevant = true) ONLY IF it matches EITHER of these criteria:
(a) The user searched with some remembered detail (keyword, face, date) and got wrong/no/incomplete results. The record MUST contain at least one concrete remembered attribute (a person, place, object, color, date/timeframe, or specific search term used).
(b) The user expected to find specific content (a photo, album, folder) that should be retrievable, but it is entirely missing or inaccessible. It must clearly describe previously-existing content that vanished.

A record is INVALID noise (is_retrieval_relevant = false) IF it is:
- A bare frustration statement with no retrievable detail or specifics (e.g., "where is my photos so", "can't find stuff", "difficult to find images").
- A generic complaint about the UI, updates, or crashes without a specific photo retrieval story.
- Generic praise, pricing complaints, or issues completely unrelated to finding photos.

Examples:
1. "Most of my albums/folders are missing, and none of the permissions and settings fix the issue." -> TRUE (Matches mode b)
2. "where is my photos so" -> FALSE (Bare frustration statement with zero specifics)
3. "why did you have to screw up the magic eraser? guess it depends on which Android model you have" -> FALSE (Generic UI complaint)
4. "I'm trying to look up pictures of my dog from last summer but it just shows screenshots." -> TRUE (Matches mode a - concrete remembered attribute 'dog' and 'last summer')

Records:
"""
    for r in batch:
        prompt += f"ID: {r['id']} | Text: {r['raw_text']}\n"
        
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': BatchRelevanceCheck,
                'temperature': 0.1
            },
        )
        return json.loads(response.text)
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg or 'quota' in error_msg.lower():
            logger.error(f"QUOTA EXCEEDED (429). Checkpointing and exiting gracefully.")
            return "QUOTA_EXCEEDED"
        logger.error(f"Gemini API error: {e}")
        return None

def run():
    parser = argparse.ArgumentParser(description="Run LLM Relevance Filter on a Sample")
    parser.add_argument("--resume", action="store_true", help="Resume processing the existing sample")
    args = parser.parse_args()

    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'discovery_engine.db')
    db = sqlite3.connect(db_path)
    
    if not args.resume:
        setup_sample(db)
    else:
        logger.info("Resuming existing sample processing...")

    BATCH_SIZE = 50
    target_count = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_sample_target = 1").fetchone()[0]
    total_processed = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_sample_target = 1 AND is_retrieval_relevant IS NOT NULL").fetchone()[0]
    relevant_count = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_sample_target = 1 AND is_retrieval_relevant = 1").fetchone()[0]
    irrelevant_count = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_sample_target = 1 AND is_retrieval_relevant = 0").fetchone()[0]
    api_calls = 0

    logger.info(f"Starting totals - Processed: {total_processed}/{target_count}, Relevant: {relevant_count}, Irrelevant: {irrelevant_count}")

    while True:
        rows = db.execute("SELECT id, raw_text FROM feedback_records WHERE is_sample_target = 1 AND is_retrieval_relevant IS NULL LIMIT ?", (BATCH_SIZE,)).fetchall()
        if not rows:
            logger.info(f"✅ FULLY COMPLETE: All {target_count} target records processed successfully!")
            break
            
        batch = [{"id": r[0], "raw_text": r[1]} for r in rows]
        
        result_data = process_batch(batch)
        if result_data == "QUOTA_EXCEEDED":
            logger.info("🛑 STOPPED: Quota exceeded. Checkpoint saved.")
            break
            
        api_calls += 1
        
        if result_data and "results" in result_data:
            updates = []
            for res in result_data["results"]:
                updates.append((res["is_retrieval_relevant"], res["id"]))
                if res["is_retrieval_relevant"]:
                    relevant_count += 1
                else:
                    irrelevant_count += 1
            
            if updates:
                db.executemany("UPDATE feedback_records SET is_retrieval_relevant = ? WHERE id = ?", updates)
                db.commit()
                total_processed += len(updates)
                logger.info(f"Processed: {total_processed}/{target_count} | Relevant: {relevant_count} | Irrelevant: {irrelevant_count} | API Calls: {api_calls}")
            
        time.sleep(4.5)

if __name__ == "__main__":
    run()
