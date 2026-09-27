import os
import sys
import sqlite3
import numpy as np
from google import genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'discovery_engine.db')

NEW_QUERIES = [
    "The small cafe we went to during our Goa trip",
    "The picture of the medicine I took when I was sick last year",
    "I know she was holding a blue coffee mug",
    "Photos from a few days after my birthday",
    "I'm looking for a rainy day at a cafe",
    "My photos disappeared after I backed up"
]

def verify_chips():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT cluster_id, label, centroid FROM clusters WHERE centroid IS NOT NULL")
    clusters = cursor.fetchall()
    
    parsed_clusters = []
    for cid, label, blob in clusters:
        vec = np.frombuffer(blob, dtype=np.float32)
        parsed_clusters.append((cid, label, vec, float(np.linalg.norm(vec))))
        
    print("=== Checking New Chips ===")
    
    for query in NEW_QUERIES:
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
                
        print(f"Dist: {min_dist:.4f} | Pred: {pred_cid} ({pred_label}) | Query: '{query}'")

if __name__ == "__main__":
    verify_chips()
