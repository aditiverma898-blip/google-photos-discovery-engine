import os
import sys
import json
import asyncio
import logging

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_pool
from synthesis.synthesizer import generate_synthesis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

import os
import sys
import json
import asyncio
import logging

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_pool
from synthesis.synthesizer import generate_synthesis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_synthesis_pipeline():
    """Fetches real verified cluster data, runs AI synthesis, and stores answers."""
    pool = await get_pool()
    
    try:
        # 1. Fetch Cluster Metadata
        logger.info("Fetching cluster metadata and live verified counts from database...")
        async with pool.execute("""
            SELECT cluster_id, label, description, severity_score, top_failure_points
            FROM clusters
            ORDER BY severity_score DESC
        """) as cursor:
            cluster_rows = await cursor.fetchall()
            
        if not cluster_rows:
            logger.error("No clusters found in the database. Cannot run synthesis.")
            return
            
        clusters = []
        for r in cluster_rows:
            c_dict = dict(r)
            cid = c_dict['cluster_id']
            try:
                c_dict['top_failure_points'] = json.loads(c_dict['top_failure_points'] or '[]')
            except Exception:
                c_dict['top_failure_points'] = []
                
            # Fetch real verified complaints count
            async with pool.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(CASE WHEN is_retrieval_relevant = 1 THEN 1 ELSE 0 END) as verified_count
                FROM feedback_records 
                WHERE cluster_id = ?
            """, (cid,)) as cnt_cur:
                cnt_row = await cnt_cur.fetchone()
                total_cnt = cnt_row[0] or 0
                verified_cnt = cnt_row[1] or 0
                
            c_dict['verified_n'] = verified_cnt
            c_dict['record_count'] = verified_cnt
            c_dict['total_n'] = total_cnt
            c_dict['severity_display'] = f"{c_dict['severity_score'] * 10:.1f}/10"
            
            # Fetch verified representative quotes
            async with pool.execute("""
                SELECT id, raw_text, source, remembered_attributes, forgotten_attributes,
                       search_strategy, failure_point, emotional_signal
                FROM feedback_records
                WHERE cluster_id = ? AND is_retrieval_relevant = 1 AND length(raw_text) > 30
                ORDER BY length(raw_text) DESC
                LIMIT 8
            """, (cid,)) as q_cur:
                q_rows = await q_cur.fetchall()
                
            verified_quotes = []
            for qr in q_rows:
                verified_quotes.append({
                    "id": qr[0],
                    "quote": qr[1].strip(),
                    "source": qr[2],
                    "remembered": qr[3],
                    "forgotten": qr[4],
                    "strategy": qr[5],
                    "failure": qr[6],
                    "emotional_signal": qr[7]
                })
            c_dict['representative_quotes'] = verified_quotes
            clusters.append(c_dict)
            
            # Keep clusters table record_count synchronized with verified count
            await pool.execute("UPDATE clusters SET record_count = ? WHERE cluster_id = ?", (verified_cnt, cid))
            
        await pool.commit()
        logger.info(f"Loaded {len(clusters)} clusters with live verified data for synthesis context.")
        for c in clusters:
            logger.info(f"  Cluster {c['cluster_id']}: '{c['label']}' | Verified n={c['verified_n']} | Severity={c['severity_display']}")
        
        # 2. Run Synthesis Generation
        logger.info("Starting AI Synthesis Engine with Gemini...")
        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(None, lambda: generate_synthesis(clusters))
        
        if not answers:
            logger.error("Synthesis generation failed or returned empty.")
            return
            
        # 3. Store Results
        logger.info("Clearing old synthesis answers from database...")
        await pool.execute("DELETE FROM synthesis_answers")
        
        insert_query = """
        INSERT INTO synthesis_answers (question_id, question_text, answer_text, evidence)
        VALUES (?, ?, ?, ?)
        """
        
        for ans in answers:
            await pool.execute(
                insert_query,
                (
                    ans['question_id'],
                    ans['question_text'],
                    ans['answer_text'],
                    json.dumps(ans['evidence'])
                )
            )
        await pool.commit()
        logger.info(f"Successfully stored {len(answers)} synthesized answers in the database.")
            
        # 4. Also update fallback MOCK_SYNTHESIS in api/mock_data.py
        mock_data_path = os.path.join(os.path.dirname(__file__), '..', 'api', 'mock_data.py')
        try:
            with open(mock_data_path, 'r', encoding='utf-8') as f:
                content = f.read()
            mock_synthesis_items = []
            for ans in answers:
                mock_synthesis_items.append({
                    "question_id": ans['question_id'],
                    "question_text": ans['question_text'],
                    "answer_text": ans['answer_text'],
                    "evidence": ans['evidence']
                })
            new_block = f"MOCK_SYNTHESIS = {json.dumps(mock_synthesis_items, indent=4)}"
            import re
            content = re.sub(r'MOCK_SYNTHESIS\s*=\s*\[[\s\S]*?\n\]', lambda m: new_block, content)
            with open(mock_data_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Updated MOCK_SYNTHESIS fallback in api/mock_data.py.")
        except Exception as me:
            logger.warning(f"Could not update mock_data.py fallback: {me}")
            
        # Print summary
        print("\n=== REGENERATED AI SYNTHESIS SUMMARY ===")
        for ans in answers:
            print(f"\nQ{ans['question_id']}: {ans['question_text']}")
            print(f"Answer: {ans['answer_text']}")
            print(f"Evidence: {ans['evidence']}")
        print("========================================\n")

    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(run_synthesis_pipeline())

