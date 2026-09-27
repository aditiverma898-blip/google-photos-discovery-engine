import sqlite3

conn = sqlite3.connect('backend/data/discovery_engine.db')
c = conn.cursor()

keywords_cluster_4 = ['meme', 'screenshot', 'receipt', 'quote', 'infographic', 'comic', 'document', 'ocr', 'text in image']
keywords_cluster_5 = ['running', 'dancing', 'walking', 'playing', 'swimming', 'cooking', 'barking', 'action', 'birthday', 'wedding', 'concert', 'graduation', 'party', 'video of']

print("=== CLUSTER 4 KEYWORDS (Abstract / Meme / Screenshot) ===")
for kw in keywords_cluster_4:
    c.execute("SELECT COUNT(*) FROM feedback_records WHERE lower(raw_text) LIKE ?", (f"%{kw}%",))
    cnt = c.fetchone()[0]
    c.execute("SELECT cluster_id, COUNT(*) FROM feedback_records WHERE lower(raw_text) LIKE ? GROUP BY cluster_id", (f"%{kw}%",))
    dist = dict(c.fetchall())
    c.execute("SELECT COUNT(*) FROM feedback_records WHERE lower(raw_text) LIKE ? AND is_retrieval_relevant = 1", (f"%{kw}%",))
    rel = c.fetchone()[0]
    print(f"'{kw}': total={cnt} | verified_relevant={rel} | cluster_dist={dist}")

print("\n=== CLUSTER 5 KEYWORDS (Action / Event / Dynamic Recall) ===")
for kw in keywords_cluster_5:
    c.execute("SELECT COUNT(*) FROM feedback_records WHERE lower(raw_text) LIKE ?", (f"%{kw}%",))
    cnt = c.fetchone()[0]
    c.execute("SELECT cluster_id, COUNT(*) FROM feedback_records WHERE lower(raw_text) LIKE ? GROUP BY cluster_id", (f"%{kw}%",))
    dist = dict(c.fetchall())
    c.execute("SELECT COUNT(*) FROM feedback_records WHERE lower(raw_text) LIKE ? AND is_retrieval_relevant = 1", (f"%{kw}%",))
    rel = c.fetchone()[0]
    print(f"'{kw}': total={cnt} | verified_relevant={rel} | cluster_dist={dist}")

print("\n=== SAMPLES OF RELEVANT RECORDS MATCHING KEYWORDS ===")
print("--- Screenshot / Document / Text samples ---")
c.execute("SELECT id, cluster_id, raw_text FROM feedback_records WHERE (lower(raw_text) LIKE '%screenshot%' OR lower(raw_text) LIKE '%document%' OR lower(raw_text) LIKE '%meme%') AND is_retrieval_relevant = 1 LIMIT 5")
for r in c.fetchall():
    print(f"ID {r[0]} (Current Cluster {r[1]}): {r[2][:120]}...")

print("\n--- Event / Action / Video samples ---")
c.execute("SELECT id, cluster_id, raw_text FROM feedback_records WHERE (lower(raw_text) LIKE '%birthday%' OR lower(raw_text) LIKE '%wedding%' OR lower(raw_text) LIKE '%video%') AND is_retrieval_relevant = 1 LIMIT 5")
for r in c.fetchall():
    print(f"ID {r[0]} (Current Cluster {r[1]}): {r[2][:120]}...")
