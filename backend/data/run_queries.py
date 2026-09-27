import sqlite3

db = sqlite3.connect('discovery_engine.db')

print('--- Query 1 ---')
try:
    print(db.execute('SELECT COUNT(*) FROM feedback_records;').fetchall())
except Exception as e:
    print('Error:', e)

print('\n--- Query 2 ---')
try:
    print(db.execute('SELECT COUNT(*) FROM feedback_records WHERE is_retrieval_attempt = true;').fetchall())
except Exception as e:
    print('Error:', e)
    print("Fallback: PRAGMA table_info(feedback_records)")
    print(db.execute('PRAGMA table_info(feedback_records)').fetchall())

print('\n--- Query 3 ---')
try:
    print(db.execute('SELECT COUNT(*) FROM feedback_records WHERE is_retrieval_attempt = false;').fetchall())
except Exception as e:
    print('Error:', e)

print('\n--- Query 4 ---')
try:
    print(db.execute('SELECT cluster_id, label, record_count FROM clusters;').fetchall())
except Exception as e:
    print('Error:', e)

print('\n--- Query 5 ---')
try:
    print(db.execute('SELECT DISTINCT label FROM clusters;').fetchall())
except Exception as e:
    print('Error:', e)
