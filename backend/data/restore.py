import sqlite3

db = sqlite3.connect('discovery_engine.db')
db.execute("""
    INSERT OR REPLACE INTO clusters (cluster_id, label, description, severity_score, top_failure_points) 
    VALUES (0, 'Missing Photos and Albums', 'Users report missing photos, albums, or scattered folders after updates or backups.', 0.90, '["Photos missing after backup", "Scattered folders"]')
""")
db.commit()
print("Cluster 0 Restored")
