import os
import sys
import sqlite3
import struct
import time
import logging
from google import genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'discovery_engine.db')

EXAMPLES = {
    1: [
        "Photos with a yellow taxi in the background",
        "Pictures where someone is holding a blue mug",
        "Look for the photo with the red fire extinguisher",
        "Find the image with a brick wall behind us",
        "Photos of the park with a statue in the distance"
    ],
    2: [
        "Photos from a few days after my birthday",
        "Pictures taken the weekend before Halloween",
        "Images from the day after we visited Paris",
        "Photos from three weeks ago at the cabin",
        "Pictures taken right before graduation"
    ],
    3: [
        "Photos on a gloomy rainy day",
        "Pictures with a moody aesthetic",
        "Images showing a bright sunny afternoon",
        "Photos with a sad atmospheric vibe",
        "Pictures taken in the freezing snow"
    ],
    4: [
        "Screenshot of a funny cat meme",
        "Meme about software engineering",
        "Quote about persistence and hard work",
        "Abstract painting with bright colors",
        "Funny text message screenshot"
    ],
    5: [
        "Video of my dog barking at the TV",
        "Photo of me blowing out birthday candles",
        "Pictures of people running in the marathon",
        "Video of the baby taking first steps",
        "Photos of us jumping in the pool"
    ]
}

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key)

def update_centroids():
    client = get_gemini_client()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT cluster_id, label, description, top_failure_points FROM clusters")
    clusters = cursor.fetchall()
    
    for cluster_id, label, description, top_fps in clusters:
        if cluster_id == 0:
            continue # Skip missing photos out of scope
            
        examples_text = " ".join(EXAMPLES.get(cluster_id, []))
        content_to_embed = f"Cluster: {label}. Description: {description}. Top issues: {top_fps}. Example Searches: {examples_text}"
        
        logger.info(f"Embedding Cluster {cluster_id}: {content_to_embed}")
        
        resp = client.models.embed_content(model="gemini-embedding-2", contents=content_to_embed)
        vec = resp.embeddings[0].values
        centroid_blob = struct.pack(f"{len(vec)}f", *vec)
        
        cursor.execute("UPDATE clusters SET centroid = ? WHERE cluster_id = ?", (centroid_blob, cluster_id))
        conn.commit()
        time.sleep(1)
        
    logger.info("Successfully updated centroids!")

if __name__ == "__main__":
    update_centroids()
