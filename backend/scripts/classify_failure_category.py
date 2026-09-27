import os
import sys
import json
import time
import sqlite3
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'discovery_engine.db')

SYSTEM_INSTRUCTION = """
You are an expert product analyst categorizing user complaints about Google Photos.
You must classify each user complaint into EXACTLY ONE of two categories:

1. 'vague_memory_retrieval':
   - The user remembers some attribute (time, place, person, object, scene, event, mood, keyword) and the photo/media exists, but search, timeline scrolling, or browsing failed to surface it.
   - The failure is a retrieval/memory-matching failure: bridging incomplete human memory to existing content.
   - Examples:
     * "I know she was holding a blue coffee mug but searching 'blue mug' gives me nothing" -> vague_memory_retrieval
     * "Pixel 10. Forced Updates. TEXT/SUBJECT search is FAIL. 'Car Engine' - have 100s of repair photos But Only 15 Show?" -> vague_memory_retrieval
     * "Ca't find pic from month of Nov 2023 and month of 2024 thanks" -> vague_memory_retrieval
     * "Searching for old pictures is difficult—you have to scroll down through. please bring back the search icon" -> vague_memory_retrieval
     * "I ask for 'yellow truck' and it finds 2 out of the 10 different days I had taken pictures of yellow trucks." -> vague_memory_retrieval

2. 'data_loss_sync':
   - The content is missing, deleted, purged, or inaccessible due to backup, sync, update, device change, or permissions issues, independent of any memory gap.
   - The user has no memory ambiguity; the content was wiped, corrupted, desynchronized, or trapped in an inaccessible locked folder/domain.
   - Examples:
     * "Lost my favorite photos tag when backing up to a new device" -> data_loss_sync
     * "where is tha locked folder" -> data_loss_sync
     * "photos missing after backup" -> data_loss_sync
     * "Lost 10+ years of photos yesterday. Need urgent help to get them back" -> data_loss_sync
     * "Somehow you guys decided to purge my whole 2020 year of pictures and videos, I tried to stop it and my screen went black. And all my videos are gone now" -> data_loss_sync
     * "Shared album photos went missing after user deleted them from their phone even after I backed up" -> data_loss_sync
     * "Be careful with this app. If you have important photos don't trust it to back it up on the cloud and remove it from your device" -> data_loss_sync

3. 'none_other':
   - The complaint does not fit clearly into either of the above categories, or is too vague to classify, or is completely unrelated to photo retrieval/sync loss.
   - Examples:
     * "App is slow" -> none_other
     * "Why does this cost so much" -> none_other
     * "I hate the new update" -> none_other
"""

CLASSIFY_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "INTEGER"},
            "failure_category": {
                "type": "STRING",
                "enum": ["vague_memory_retrieval", "data_loss_sync", "none_other"]
            },
            "confidence": {"type": "NUMBER"},
            "reason": {"type": "STRING"}
        },
        "required": ["id", "failure_category", "confidence", "reason"]
    }
}

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key)

def classify_batch(client, records: list[dict], max_retries: int = 3) -> list[dict]:
    items_text = ""
    for r in records:
        items_text += f"Record ID: {r['id']}\nComplaint: \"{r['raw_text']}\"\n\n"

    prompt = f"Classify the following {len(records)} user complaints into 'vague_memory_retrieval', 'data_loss_sync', or 'none_other':\n\n{items_text}"

    for attempt in range(max_retries):
        try:
            logger.info(f"Calling Gemini API for batch of {len(records)} items (Attempt {attempt+1}/{max_retries})...")
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CLASSIFY_SCHEMA,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1
                )
            )
            parsed = json.loads(response.text)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "resource_exhausted" in err_str:
                wait_time = (attempt + 1) * 10
                logger.warning(f"Rate limited (429). Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.warning(f"Classification call failed: {e}. Retrying in 4s...")
                time.sleep(4)
                
    # Heuristic fallback if batch API fails
    logger.warning(f"Batch LLM failed after retries. Applying criteria heuristic fallback for {len(records)} items.")
    fallback_results = []
    loss_keywords = ["lost", "missing", "disappeared", "deleted", "backup", "sync", "locked folder", "device", "transfer", "gone", "can't find my album", "all my photos are gone"]
    for r in records:
        txt = r['raw_text'].lower()
        if any(k in txt for k in loss_keywords) or r.get('cluster_id') == 0:
            cat = "data_loss_sync"
        else:
            cat = "vague_memory_retrieval"
        fallback_results.append({"id": r['id'], "failure_category": cat, "reason": "Heuristic criteria match fallback", "confidence": 0.1})
    return fallback_results

def run_classification():
    client = get_client()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get verified relevant records that haven't been categorized yet
    cursor.execute("""
        SELECT id, raw_text, cluster_id 
        FROM feedback_records 
        WHERE is_retrieval_relevant = 1 AND (failure_category IS NULL OR failure_category = '')
        ORDER BY id ASC
    """)
    pending_records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM feedback_records WHERE is_retrieval_relevant = 1")
    total_relevant = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM feedback_records WHERE is_retrieval_relevant = 1 AND failure_category IS NOT NULL")
    already_categorized = cursor.fetchone()[0]

    logger.info(f"Total verified relevant records: {total_relevant}")
    logger.info(f"Already categorized: {already_categorized}, Pending: {len(pending_records)}")

    if not pending_records:
        logger.info("All verified relevant records already categorized.")
        _print_summary(cursor)
        conn.close()
        return

    BATCH_SIZE = 30
    batches = [pending_records[i:i + BATCH_SIZE] for i in range(0, len(pending_records), BATCH_SIZE)]
    logger.info(f"Processing in {len(batches)} batches of up to {BATCH_SIZE} records...")

    processed = already_categorized
    for idx, b in enumerate(batches):
        batch_dicts = [{"id": r[0], "raw_text": r[1], "cluster_id": r[2]} for r in b]
        results = classify_batch(client, batch_dicts)

        for res in results:
            rid = res.get("id")
            cat = res.get("failure_category")
            conf = res.get("confidence")
            reason = res.get("reason")
            if rid and cat in ("vague_memory_retrieval", "data_loss_sync", "none_other"):
                cursor.execute(
                    "UPDATE feedback_records SET failure_category = ?, classification_confidence = ?, classification_reason = ? WHERE id = ?", 
                    (cat, conf, reason, rid)
                )

        conn.commit()
        processed += len(b)
        logger.info(f"Progress: {processed}/{total_relevant} records categorized (Batch {idx+1}/{len(batches)}).")
        time.sleep(0.8) # Graceful pacing

    logger.info("Classification pass finished.")
    _print_summary(cursor)
    conn.close()

def _print_summary(cursor):
    print("\n" + "=" * 50)
    print("=== FAILURE CATEGORY BREAKDOWN SUMMARY ===")
    cursor.execute("""
        SELECT failure_category, COUNT(*) 
        FROM feedback_records 
        WHERE is_retrieval_relevant = 1 
        GROUP BY failure_category
    """)
    rows = cursor.fetchall()
    for cat, cnt in rows:
        print(f"  {cat or 'uncategorized'}: {cnt} complaints")

    print("\n=== CLUSTER BREAKDOWN BY CATEGORY ===")
    cursor.execute("""
        SELECT c.cluster_id, c.label,
               SUM(CASE WHEN f.failure_category = 'vague_memory_retrieval' THEN 1 ELSE 0 END) as vague_mem,
               SUM(CASE WHEN f.failure_category = 'data_loss_sync' THEN 1 ELSE 0 END) as data_loss,
               SUM(CASE WHEN f.is_retrieval_relevant = 1 THEN 1 ELSE 0 END) as total_verified
        FROM clusters c
        LEFT JOIN feedback_records f ON c.cluster_id = f.cluster_id
        GROUP BY c.cluster_id
        ORDER BY vague_mem DESC
    """)
    for r in cursor.fetchall():
        cid, label, v_mem, d_loss, tot = r
        print(f"Cluster {cid}: '{label}' -> Vague Memory: {v_mem} | Data Loss/Sync: {d_loss} | Total Verified: {tot}")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    run_classification()
