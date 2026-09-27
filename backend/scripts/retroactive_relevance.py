import os
import sqlite3
import json
import time
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
    is_retrieval_relevant: bool = Field(description="True if the user is explicitly describing a failed attempt to search for, retrieve, or locate a specific photo/album. False if it is just general app praise, UI complaints, or crash reports without a photo search story.")

class BatchRelevanceCheck(BaseModel):
    results: list[RelevanceCheck]

def process_batch(batch):
    prompt = "Evaluate the following user feedback records from Google Photos. Determine if each record is a genuine photo retrieval/search failure. Returns a JSON array mapping 'id' to 'is_retrieval_relevant'.\n\nRecords:\n"
    for r in batch:
        prompt += f"ID: {r['id']} | Text: {r['raw_text']}\n"
        
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': BatchRelevanceCheck,
                'temperature': 0.1
            },
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None

def run():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'discovery_engine.db')
    db = sqlite3.connect(db_path)
    
    BATCH_SIZE = 50 # 50 records per API call
    
    while True:
        rows = db.execute("SELECT id, raw_text FROM feedback_records WHERE is_retrieval_relevant IS NULL LIMIT ?", (BATCH_SIZE,)).fetchall()
        if not rows:
            logger.info("All records processed!")
            break
            
        batch = [{"id": r[0], "raw_text": r[1]} for r in rows]
        logger.info(f"Processing batch of {len(batch)} records...")
        
        result_data = process_batch(batch)
        if result_data and "results" in result_data:
            # Update DB
            updates = []
            for res in result_data["results"]:
                updates.append((res["is_retrieval_relevant"], res["id"]))
            
            if updates:
                db.executemany("UPDATE feedback_records SET is_retrieval_relevant = ? WHERE id = ?", updates)
                db.commit()
                logger.info(f"Successfully updated {len(updates)} records.")
            
        # Free tier is 15 RPM -> 1 request per 4 seconds.
        # We process 50 records per request. Total time = 12800 / 50 = 256 requests.
        # 256 requests * 4.5 seconds = 1152 seconds = 19 minutes.
        time.sleep(4.5)

if __name__ == "__main__":
    run()
