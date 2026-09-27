import os
import json
import asyncio
import logging
from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GenAI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
EMBEDDING_MODEL = "gemini-embedding-2"

async def embed_single(record: dict, semaphore: asyncio.Semaphore) -> dict:
    failure = record.get("failure_point", "")
    strategy = record.get("search_strategy", "")
    text = f"{failure} | {strategy}".strip(" |")
    if not text:
        text = "photo retrieval search failure"

    async with semaphore:
        for attempt in range(3):
            try:
                resp = await client.aio.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=text
                )
                record["embedding"] = resp.embeddings[0].values
                return record
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = 12.0 * (attempt + 1)
                    logger.warning(f"[embedder] 429 quota wait {wait:.1f}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning(f"[embedder] Record {record.get('id')} error: {e}")
                    await asyncio.sleep(2.0)
        return record

async def embed_records(records: list[dict]) -> list[dict]:
    """
    Takes a list of records, generates embeddings via gemini-embedding-2,
    and returns records with the 'embedding' vector added.
    """
    if not records:
        return []

    logger.info(f"Generating embeddings for {len(records)} records...")
    semaphore = asyncio.Semaphore(8)
    
    # Process in chunks of 25 for steady progress logging
    chunk_size = 25
    embedded_all = []
    
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        tasks = [embed_single(r, semaphore) for r in chunk]
        results = await asyncio.gather(*tasks)
        embedded_chunk = [r for r in results if r.get("embedding") is not None]
        embedded_all.extend(embedded_chunk)
        logger.info(f"[embedder] Progress: {len(embedded_all)}/{len(records)} records embedded")
        await asyncio.sleep(1.0)
        
    return embedded_all
