import os
import sys
import sqlite3
import numpy as np
from google import genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'discovery_engine.db')

TEST_QUERIES = [
    # Cluster 1: Background Object
    ("Where is the picture with the yellow taxi in the background?", 1),
    ("I need the photo of us where you can see a blue coffee mug.", 1),
    ("Looking for the image that has a red fire extinguisher on the wall.", 1),
    ("Photos with a brick wall behind my family.", 1),
    
    # Cluster 2: Relative Time and Space
    ("Photos from a few days after my birthday", 2),
    ("Pictures from the weekend before Halloween", 2),
    ("Images taken right after graduation", 2),
    ("Photos from two weeks ago at the park", 2),
    
    # Cluster 3: Aesthetic and Weather
    ("Pictures on a gloomy rainy day", 3),
    ("Photos with a moody aesthetic vibe", 3),
    ("Looking for a bright sunny afternoon photo", 3),
    ("Pictures taken during a heavy snowstorm", 3),
    
    # Cluster 4: Abstract/Meme
    ("Screenshot of a funny software engineering meme", 4),
    ("Looking for the quote about persistence", 4),
    ("A funny text message screenshot", 4),
    ("Abstract colorful painting", 4),
    
    # Cluster 5: Action/Event
    ("Video of the dog barking at the TV", 5),
    ("Pictures of people running a marathon", 5),
    ("Photo of me blowing out the candles on my cake", 5),
    ("Video of the baby taking first steps", 5)
]

def eval_search():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT cluster_id, label, centroid FROM clusters WHERE centroid IS NOT NULL AND cluster_id != 0")
    clusters = cursor.fetchall()
    
    parsed_clusters = []
    for cid, label, blob in clusters:
        vec = np.frombuffer(blob, dtype=np.float32)
        parsed_clusters.append((cid, label, vec, float(np.linalg.norm(vec))))
        
    print("=== Distance Tuning on 20 Labeled Test Queries ===")
    
    for query, expected_cid in TEST_QUERIES:
        resp = client.models.embed_content(model="gemini-embedding-2", contents=query)
        q_vec = np.array(resp.embeddings[0].values, dtype=np.float32)
        q_norm = float(np.linalg.norm(q_vec))
        
        min_dist = float("inf")
        pred_cid = None
        pred_label = None
        
        for cid, label, c_vec, c_norm in parsed_clusters:
            sim = float(np.dot(q_vec, c_vec)) / max(q_norm * c_norm, 1e-9)
            dist = max(0.0, 1.0 - sim)
            if dist < min_dist:
                min_dist = dist
                pred_cid = cid
                pred_label = label
                
        match = "PASS" if pred_cid == expected_cid else "FAIL"
        print(f"[{match}] Dist: {min_dist:.4f} | Expected: {expected_cid} | Pred: {pred_cid} ({pred_label}) | Query: '{query}'")

if __name__ == "__main__":
    eval_search()
