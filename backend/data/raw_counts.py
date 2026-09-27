import sqlite3
import sys

def run():
    try:
        db = sqlite3.connect('discovery_engine.db')
        
        # 1. Total rows in feedback_records
        res1 = db.execute("SELECT COUNT(*) FROM feedback_records;").fetchone()
        print(res1[0])
        
        # 2. Count where is_retrieval_attempt = true
        try:
            res2 = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_retrieval_attempt = true;").fetchone()
            print(res2[0])
        except Exception as e:
            print(f"Error: {e}")
            
        # 3. Count where is_retrieval_attempt = false
        try:
            res3 = db.execute("SELECT COUNT(*) FROM feedback_records WHERE is_retrieval_attempt = false;").fetchone()
            print(res3[0])
        except Exception as e:
            print(f"Error: {e}")
            
        # 4. cluster_name and COUNT(*)
        try:
            res4 = db.execute("SELECT label, COUNT(*) FROM clusters GROUP BY label;").fetchall()
            for r in res4:
                print(f"{r[0]}: {r[1]}")
        except Exception as e:
            print(f"Error: {e}")
            
        # 5. List of DISTINCT cluster_name values
        try:
            res5 = db.execute("SELECT DISTINCT label FROM clusters;").fetchall()
            for r in res5:
                print(r[0])
        except Exception as e:
            print(f"Error: {e}")
            
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    run()
