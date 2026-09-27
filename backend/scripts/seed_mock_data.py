import os
import sys
import json
import sqlite3
import struct
from google import genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.mock_data import MOCK_CLUSTERS, MOCK_SYNTHESIS

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
db_path = os.path.join(os.path.dirname(__file__), "..", "data", "discovery_engine.db")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def seed():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Insert clusters
    for i, c in enumerate(MOCK_CLUSTERS):
        response = client.models.embed_content(
            model="gemini-embedding-2",
            contents=f"{c['label']} {c['description']}"
        )
        embedding = response.embeddings[0].values
        centroid_blob = struct.pack(f"{len(embedding)}f", *embedding)
        
        cursor.execute("""
            INSERT OR REPLACE INTO clusters (
                cluster_id, label, description, record_count, 
                source_diversity, severity_score, top_failure_points, 
                representative_quotes, centroid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c["cluster_id"],
            c["label"],
            c["description"],
            c["size"],
            json.dumps({"appstore": c["size"] // 2, "reddit": c["size"] // 4, "helpforum": c["size"] // 4}),
            c["severity_score"],
            json.dumps(c["top_failure_points"]),
            json.dumps(c["representative_quotes"]),
            centroid_blob
        ))
        
        # Insert a few mock feedback records per cluster
        for j, fp in enumerate(c["top_failure_points"]):
            quote_val = c['representative_quotes'][0]
            quote_str = quote_val.get("quote", "") if isinstance(quote_val, dict) else quote_val
            rec_text = f"User complained about: {fp}. {quote_str}"
            rec_resp = client.models.embed_content(
                model="gemini-embedding-2",
                contents=rec_text
            )
            rec_emb = rec_resp.embeddings[0].values
            rec_blob = struct.pack(f"{len(rec_emb)}f", *rec_emb)
            
            cursor.execute("""
                INSERT OR REPLACE INTO feedback_records (
                    url_id, cluster_id, source_platform, raw_text, photo_type, 
                    remembered_attributes, forgotten_attributes, 
                    search_strategy, failure_point, workaround, emotional_signal, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"mock_{c['cluster_id']}_{j}",
                c["cluster_id"],
                "appstore",
                rec_text,
                "photo",
                "{}",
                "{}",
                "semantic search",
                fp,
                "none",
                "frustrated",
                rec_blob
            ))
        
    # Insert synthesis
    for s in MOCK_SYNTHESIS:
        cursor.execute("""
            INSERT OR REPLACE INTO synthesis_answers (
                question_text, answer_text, evidence
            ) VALUES (?, ?, ?)
        """, (
            s["question"],
            s["answer"],
            json.dumps(s["cited_clusters"])
        ))
        
    conn.commit()
    conn.close()
    print("Successfully seeded mock data into SQLite database!")

if __name__ == "__main__":
    seed()
