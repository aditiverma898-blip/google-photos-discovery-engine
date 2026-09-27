import sqlite3
import re
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "discovery_engine.db")

def patch_synthesis_answers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    rows = cursor.execute("SELECT question_id, answer_text FROM synthesis_answers").fetchall()
    
    updated_count = 0
    for row in rows:
        q_id = row['question_id']
        text = row['answer_text']
        
        # Regex to find "severity 0.61" or similar and replace with "severity 6.1/10"
        def repl(match):
            score_str = match.group(1)
            try:
                score = float(score_str)
                formatted = f"{score * 10:.1f}/10"
                return f"severity {formatted}"
            except ValueError:
                return match.group(0)
                
        new_text = re.sub(r'severity\s+(0\.\d+)', repl, text)
        
        if new_text != text:
            cursor.execute("UPDATE synthesis_answers SET answer_text = ? WHERE question_id = ?", (new_text, q_id))
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully patched {updated_count} synthesis answers.")

if __name__ == "__main__":
    patch_synthesis_answers()
