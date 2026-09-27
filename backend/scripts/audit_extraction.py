import os
import sys
import asyncio
import json
import logging

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def audit_extraction():
    """
    Samples 100 random records from feedback_records and writes them to a 
    markdown file for manual review of extraction quality.
    """
    pool = await get_pool()
    
    query = """
    SELECT 
        id, source_platform, raw_text, photo_type, 
        remembered_attributes, forgotten_attributes, search_strategy, failure_point
    FROM feedback_records 
    ORDER BY random() 
    LIMIT 100;
    """
    
    output_file = os.path.join(os.path.dirname(__file__), "..", "data", "extraction_audit.md")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    async with pool.acquire() as conn:
        records = await conn.fetch(query)
        
        if not records:
            logger.warning("No records found in feedback_records to audit.")
            return
            
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Extraction Quality Audit\n\n")
            f.write(f"Sampled {len(records)} records for manual review.\n\n")
            f.write("---\n\n")
            
            for i, r in enumerate(records, 1):
                f.write(f"## Record {i} (ID: {r['id']} | Source: {r['source_platform']})\n\n")
                f.write(f"**Raw Text:**\n> {r['raw_text']}\n\n")
                f.write(f"**Photo Type:** {r['photo_type']}\n")
                f.write(f"**Search Strategy:** {r['search_strategy']}\n")
                f.write(f"**Failure Point:** {r['failure_point']}\n")
                f.write(f"**Remembered Attributes:** {r['remembered_attributes']}\n")
                f.write(f"**Forgotten Attributes:** {r['forgotten_attributes']}\n\n")
                f.write("---\n\n")
                
        logger.info(f"Audit exported to {output_file}. Please review manually.")

if __name__ == "__main__":
    asyncio.run(audit_extraction())
