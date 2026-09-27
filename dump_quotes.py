import sqlite3
import json

conn = sqlite3.connect('backend/data/discovery_engine.db')
cursor = conn.cursor()
cursor.execute('''
SELECT id, cluster_id, source_platform, raw_text 
FROM feedback_records 
WHERE is_retrieval_relevant = 1 
  AND failure_category = 'vague_memory_retrieval'
  AND (raw_text LIKE '%remember%' OR raw_text LIKE '%look%' OR raw_text LIKE '%find%' OR raw_text LIKE '%know%')
LIMIT 100
''')

quotes = []
for row in cursor.fetchall():
    quotes.append({
        'id': row[0],
        'cluster': row[1],
        'source': row[2],
        'text': row[3]
    })

with open('quotes_dump.json', 'w', encoding='utf-8') as f:
    json.dump(quotes, f, indent=2)
