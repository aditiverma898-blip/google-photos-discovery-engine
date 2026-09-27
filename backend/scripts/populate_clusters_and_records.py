"""
Populates cluster centroids and maps all feedback records to their respective clusters.
Uses robust retry and immediate transaction commits.
"""

import os
import sys
import json
import sqlite3
import struct
import time
import logging
from google import genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'discovery_engine.db')

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key)

def embed_with_retry(client, text, max_retries=5):
    for attempt in range(max_retries):
        try:
            resp = client.models.embed_content(model="gemini-embedding-2", contents=text)
            return resp
        except Exception as e:
            wait = (attempt + 1) * 2
            logger.warning(f"Embedding failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Failed to embed after {max_retries} attempts.")

def populate():
    client = get_gemini_client()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. First, assign cluster_id to ALL records and COMMIT immediately!
    cursor.execute("SELECT id, raw_text, failure_point, photo_type FROM feedback_records")
    records = cursor.fetchall()
    logger.info(f"Loaded {len(records)} feedback records.")

    cluster_keywords = {
        1: ["face", "person", "people", "tag", "sister", "mom", "dad", "friend", "label", "family", "name", "who", "facial"],
        2: ["date", "year", "month", "summer", "timeline", "calendar", "2017", "2018", "2019", "2020", "2021", "2022", "old", "time", "recent", "historical", "december", "june"],
        3: ["pet", "dog", "cat", "animal", "puppy", "breed", "cats", "dogs", "pillow"],
        4: ["location", "city", "place", "gps", "map", "paris", "rome", "where", "landmark", "trip", "travel", "country", "area", "address"]
    }

    for rid, raw_text, failure_point, photo_type in records:
        text_lower = f"{raw_text or ''} {failure_point or ''} {photo_type or ''}".lower()
        scores = {cid: 0 for cid in cluster_keywords}
        for cid, kws in cluster_keywords.items():
            for kw in kws:
                if kw in text_lower:
                    scores[cid] += 1

        best_cid = max(scores, key=scores.get)
        if scores[best_cid] == 0:
            best_cid = (rid % 4) + 1

        cursor.execute("UPDATE feedback_records SET cluster_id = ? WHERE id = ?", (best_cid, rid))

    conn.commit()
    logger.info("Committed cluster_id assignments to all feedback_records!")

    # 2. Embed & Update Cluster Centroids
    cursor.execute("SELECT cluster_id, label, description, top_failure_points FROM clusters")
    clusters = cursor.fetchall()
    logger.info(f"Embedding {len(clusters)} cluster centroids...")

    for cluster_id, label, description, top_fps in clusters:
        content_to_embed = f"{label}. {description}. Top issues: {top_fps}"
        resp = embed_with_retry(client, content_to_embed)
        vec = resp.embeddings[0].values
        centroid_blob = struct.pack(f"{len(vec)}f", *vec)
        cursor.execute("UPDATE clusters SET centroid = ? WHERE cluster_id = ?", (centroid_blob, cluster_id))
        conn.commit()
        logger.info(f"Updated centroid for Cluster #{cluster_id}: {label}")
        time.sleep(1)

    # 3. Batch Embed Records in chunks of 20
    cursor.execute("SELECT id, raw_text, failure_point FROM feedback_records WHERE embedding IS NULL")
    records_to_embed = cursor.fetchall()
    logger.info(f"Embedding {len(records_to_embed)} records in batches...")

    batch_size = 20
    for i in range(0, len(records_to_embed), batch_size):
        batch = records_to_embed[i:i+batch_size]
        texts = [f"{fp or ''}. {rt or ''}" for _, rt, fp in batch]
        
        resp = embed_with_retry(client, texts)
        embeddings = resp.embeddings

        update_data = []
        for (rid, _, _), emb in zip(batch, embeddings):
            vec = emb.values
            blob = struct.pack(f"{len(vec)}f", *vec)
            update_data.append((blob, rid))

        cursor.executemany("UPDATE feedback_records SET embedding = ? WHERE id = ?", update_data)
        conn.commit()
        logger.info(f"Embedded batch {i // batch_size + 1}/{(len(records_to_embed)+batch_size-1)//batch_size} ({len(update_data)} records)")
        time.sleep(1.5)

    cursor.execute("SELECT cluster_id, count(*) FROM feedback_records GROUP BY cluster_id")
    logger.info(f"Final records per cluster: {cursor.fetchall()}")
    cursor.execute("SELECT count(*) FROM feedback_records WHERE embedding IS NOT NULL")
    logger.info(f"Total embedded records: {cursor.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    populate()
