import sqlite3
import csv
import os

def main():
    conn = sqlite3.connect('backend/data/discovery_engine.db')
    cursor = conn.cursor()

    # Get all cluster IDs
    cursor.execute("SELECT cluster_id, label FROM clusters ORDER BY cluster_id")
    clusters = cursor.fetchall()

    csv_path = 'scratch/cluster_samples.csv'
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Cluster ID', 'Cluster Label', 'Record ID', 'Source', 'Failure Category', 'Confidence', 'Reason', 'Text'])

        for cid, label in clusters:
            cursor.execute("""
                SELECT id, source_platform, source, failure_category, classification_confidence, classification_reason, raw_text
                FROM feedback_records
                WHERE cluster_id = ? AND is_retrieval_relevant = 1
                ORDER BY RANDOM()
                LIMIT 20
            """, (cid,))
            
            rows = cursor.fetchall()
            for r in rows:
                rec_id, src_plat, src, fcat, conf, reason, text = r
                final_src = src or src_plat
                writer.writerow([cid, label, rec_id, final_src, fcat, conf, reason, text])

    print(f"Exported random samples to {csv_path}")
    conn.close()

if __name__ == '__main__':
    main()
