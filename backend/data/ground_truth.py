import sqlite3

def run():
    db = sqlite3.connect('discovery_engine.db')
    
    print("--- 1. FULL SCHEMA ---")
    schemas = db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('feedback_records', 'clusters');").fetchall()
    for s in schemas:
        print(f"Table: {s[0]}")
        print(s[1])
        print()
        
    print("--- 2. CLUSTER LINKAGE ---")
    columns = [row[1] for row in db.execute("PRAGMA table_info(feedback_records)").fetchall()]
    if 'cluster_id' in columns:
        print("Yes, feedback_records has a column that links a record to a cluster. The column is named exactly: cluster_id")
    else:
        print("No cluster-to-record linkage exists in the schema.")
        
    print("\n--- 3. RELEVANCE/EXTRACTION COLUMN ---")
    # check for any boolean/status columns
    status_cols = [c for c in columns if 'status' in c or 'is_' in c or 'attempt' in c or 'relevan' in c or 'extract' in c]
    if not status_cols:
        print("Explicitly: No relevance/extraction status column exists in feedback_records.")
    else:
        print(f"Found related columns: {status_cols}")
        
    print("\n--- 4. FULL CLUSTERS TABLE RAW OUTPUT ---")
    try:
        # Get column names first to make it readable
        cluster_cols = [row[1] for row in db.execute("PRAGMA table_info(clusters)").fetchall() if row[1] != 'centroid']
        print("Columns: " + ", ".join(cluster_cols))
        rows = db.execute("SELECT cluster_id, label, description, record_count, source_diversity, severity_score, top_failure_points, representative_quotes, created_at, updated_at FROM clusters;").fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(e)
        
    print("\n--- ADDITIONAL FACT CHECK (cluster_id counts) ---")
    # The user said earlier that there was only 1 linked record. Let's see what the actual group by counts are.
    counts = db.execute("SELECT cluster_id, COUNT(*) FROM feedback_records GROUP BY cluster_id").fetchall()
    for c in counts:
        print(f"cluster_id {c[0]}: {c[1]} records in feedback_records")

if __name__ == "__main__":
    run()
