import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('discovery_engine.db')

r_reddit = db.execute("SELECT id, raw_text FROM feedback_records WHERE is_sample_target = 1 AND is_retrieval_relevant = 1 AND (source_platform LIKE '%reddit%' OR source = 'Reddit') ORDER BY RANDOM() LIMIT 3").fetchall()

r_support = db.execute("SELECT id, raw_text FROM feedback_records WHERE is_sample_target = 1 AND is_retrieval_relevant = 1 AND (source_platform LIKE '%help%' OR source_platform LIKE '%forum%' OR source = 'Google Support Community') ORDER BY RANDOM() LIMIT 3").fetchall()

print('--- Reddit ---')
for r in r_reddit:
    print(f'[{r[0]}] {r[1]}\n')

print('--- Support Community ---')
for r in r_support:
    print(f'[{r[0]}] {r[1]}\n')
