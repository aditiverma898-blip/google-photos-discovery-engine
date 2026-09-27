import os
import sys
import sqlite3
import struct
import time
from google import genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'discovery_engine.db')

def embed_cluster_zero():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    examples = "My photos disappeared after I backed up, Missing photos, Data loss, Google Photos deleted my album"
    content = f"Cluster: Missing Photos and Albums (Data Loss). Description: Out of scope complaints about missing files, backup issues, and data loss. Example Searches: {examples}"
    
    resp = client.models.embed_content(model="gemini-embedding-2", contents=content)
    vec = resp.embeddings[0].values
    blob = struct.pack(f"{len(vec)}f", *vec)
    
    cursor.execute("UPDATE clusters SET centroid = ? WHERE cluster_id = 0", (blob,))
    conn.commit()
    print("Embedded cluster 0.")

if __name__ == "__main__":
    embed_cluster_zero()
