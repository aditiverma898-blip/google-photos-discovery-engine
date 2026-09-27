import json
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from google import genai
import os
import re
import asyncio
from typing import Literal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

IN_SCOPE_SQL = "is_retrieval_relevant = 1 AND failure_category = 'vague_memory_retrieval'"
UNATTRIBUTED_SOURCE = "__unattributed__"
UNSPECIFIED_STRATEGY = "__unspecified__"
WORKAROUND_GROUP_SQL = """CASE
    WHEN workaround IS NULL OR trim(workaround) = ''
         OR lower(trim(workaround)) IN ('none', 'none reported') THEN 'no_text'
    WHEN lower(workaround) LIKE '%scroll%' THEN 'scroll_mention'
    ELSE 'other_text'
END"""

class SearchQuery(BaseModel):
    query: str

class CopilotQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=500)

async def _get_active_pool(request: Request):
    """Use the packaged dataset in read-only mode, including on cold starts."""
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        from db.connection import get_read_only_pool
        try:
            pool = await get_read_only_pool()
        except Exception as exc:
            logger.error("Discovery database unavailable: %s", exc)
            raise HTTPException(status_code=503, detail="Discovery data is unavailable. Check the packaged database.") from exc
        request.app.state.pool = pool
    return pool

def canonicalize_source(raw_src: str | None) -> str | None:
    """Map raw platform names to clean, user-facing canonical source strings."""
    if not raw_src:
        return None
    s = str(raw_src).strip().lower()
    if s in ("", "unknown", "null", "none"):
        return None
    if "reddit" in s:
        return "Reddit"
    if "play" in s:
        return "Play Store"
    if "app_store" in s or "appstore" in s or "ios" in s:
        return "App Store"
    if "youtube" in s:
        return "YouTube Comment"
    if "help" in s or "forum" in s or "support" in s:
        return "Google Support Community"
    if "twitter" in s or s == "x":
        return "Twitter/X"
    return str(raw_src).replace("_", " ").title()

@router.get("/clusters")
async def get_clusters(request: Request):
    """Returns all clusters with their metadata and source-tagged quotes."""
    pool = await _get_active_pool(request)
        
    async with pool.execute("""
        SELECT cluster_id, label, description, severity_score, top_failure_points
        FROM clusters
        ORDER BY severity_score DESC
    """) as cursor:
        rows = await cursor.fetchall()
        
    clusters = []
    missing_source_count = 0
    for r in rows:
        c = dict(r)
        c['top_failure_points'] = json.loads(c.get('top_failure_points', '[]'))
        cid = c['cluster_id']
        
        # 1. Real Record Count, Relevance states, and Failure Category Breakdown
        async with pool.execute("""
            SELECT count(*), 
                   SUM(CASE WHEN is_retrieval_relevant = 1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_retrieval_relevant = 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_retrieval_relevant IS NULL THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_retrieval_relevant = 1 AND failure_category = 'vague_memory_retrieval' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_retrieval_relevant = 1 AND failure_category = 'data_loss_sync' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_retrieval_relevant = 1 AND failure_category = 'none_other' THEN 1 ELSE 0 END)
            FROM feedback_records WHERE cluster_id = ?
        """, (cid,)) as cursor:
            row = await cursor.fetchone()
            c['record_count'] = row[0]
            c['confirmed_relevant'] = row[1] or 0
            c['confirmed_irrelevant'] = row[2] or 0
            c['unverified'] = row[3] or 0
            c['vague_memory_count'] = row[4] or 0
            c['data_loss_count'] = row[5] or 0
            c['none_other_count'] = row[6] or 0
            
        if cid == 0:
            c['primary_category'] = 'data_loss_sync'
        else:
            c['primary_category'] = 'vague_memory_retrieval'
            
        # 2. Real Source Diversity
        async with pool.execute("SELECT source, source_platform, count(*) as cnt FROM feedback_records WHERE cluster_id = ? GROUP BY source, source_platform", (cid,)) as cursor:
            src_rows = await cursor.fetchall()
            
        s_div = {}
        for sr in src_rows:
            canon = sr[0] or canonicalize_source(sr[1])
            if canon:
                s_div[canon] = s_div.get(canon, 0) + sr[2]
        
        # Calculate percentages for the frontend
        total_cluster_records = sum(s_div.values()) or 1
        s_div_percentages = {s: round((cnt / total_cluster_records) * 100, 1) for s, cnt in s_div.items()}
        c['source_diversity'] = s_div_percentages
        
        # 3. Representative Quotes
        async with pool.execute("""
            SELECT id, raw_text, source, source_platform, remembered_attributes, 
                   forgotten_attributes, search_strategy, failure_point, workaround, 
                   emotional_signal 
            FROM feedback_records 
            WHERE cluster_id = ? AND length(raw_text) > 40 
            ORDER BY classification_confidence DESC
            LIMIT 3
        """, (cid,)) as cursor:
            quote_rows = await cursor.fetchall()
            
        formatted_quotes = []
        for qr in quote_rows:
            qr_dict = dict(qr)
            canon = qr_dict.get("source") or canonicalize_source(qr_dict.get("source_platform"))
            
            if not canon:
                missing_source_count += 1
                logger.warning(f"[Missing Source] Complaint quote in cluster #{cid} has no source: '{qr_dict.get('raw_text', '')[:60]}...'. Flagged for backfill.")
                
            formatted_quotes.append({
                "id": qr_dict.get("id"),
                "text": qr_dict.get("raw_text"),
                "source": canon,
                "cluster_id": cid,
                "cluster_label": c['label'],
                "severity_score": c['severity_score'],
                "remembered_attributes": qr_dict.get("remembered_attributes"),
                "forgotten_attributes": qr_dict.get("forgotten_attributes"),
                "search_strategy": qr_dict.get("search_strategy"),
                "failure_point": qr_dict.get("failure_point"),
                "workaround": qr_dict.get("workaround"),
                "emotional_signal": qr_dict.get("emotional_signal")
            })
            
        c['is_emerging'] = (c.get('record_count', 0) <= 5 or cid in (3, 4, 5))
        c['representative_quotes'] = formatted_quotes
        clusters.append(c)
        
    # Re-rank: in-scope (vague_memory_retrieval) non-emerging first sorted by confirmed_relevant and severity, then emerging, then out-of-scope (data_loss_sync)
    clusters.sort(key=lambda x: (
        x.get('primary_category') == 'vague_memory_retrieval',
        not x.get('is_emerging', False),
        x.get('confirmed_relevant', 0) if x.get('primary_category') == 'vague_memory_retrieval' else 0,
        x.get('severity_score', 0)
    ), reverse=True)

    if missing_source_count > 0:
        logger.warning(f"Total representative complaint quotes missing source across clusters: {missing_source_count}")
        
    return {"clusters": clusters, "missing_source_count": missing_source_count}

@router.get("/clusters/{cluster_id}/records")
async def get_cluster_records(request: Request, cluster_id: int):
    """Returns raw feedback records associated with a specific cluster."""
    pool = await _get_active_pool(request)
        
    async with pool.execute("""
        SELECT id, cluster_id, source, source_platform, raw_text, photo_type, 
               remembered_attributes, forgotten_attributes, 
               search_strategy, failure_point, workaround, emotional_signal
        FROM feedback_records
        WHERE cluster_id = ?
        ORDER BY created_at DESC
    """, (cluster_id,)) as cursor:
        rows = await cursor.fetchall()
        
    records = []
    missing_source_count = 0
    for r in rows:
        item = dict(r)
        canonical_src = item.get("source") or canonicalize_source(item.get("source_platform"))
        if not canonical_src:
            missing_source_count += 1
            logger.warning(f"[Missing Source] Complaint record #{item['id']} has no source platform (raw='{item.get('source_platform')}'). Flagged for backfill.")
        item["source"] = canonical_src
        records.append(item)
        
    if missing_source_count > 0:
        logger.warning(f"Cluster #{cluster_id} has {missing_source_count} records missing source values.")
        
    return {"records": records, "missing_source_count": missing_source_count}

@router.get("/coverage")
async def get_coverage(request: Request):
    """Returns total corpus size and counts grouped by source."""
    pool = await _get_active_pool(request)
        
    async with pool.execute("SELECT source, count(*) as cnt FROM feedback_records GROUP BY source") as cursor:
        counts_raw = await cursor.fetchall()
        
    source_counts = {}
    for r in counts_raw:
        src = r[0]
        cnt = r[1]
        if src:
            canon = canonicalize_source(src)
            if canon:
                source_counts[canon] = source_counts.get(canon, 0) + cnt
            
    async with pool.execute("""
        SELECT 
            SUM(CASE WHEN is_retrieval_relevant = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_retrieval_relevant = 1 AND failure_category = 'vague_memory_retrieval' THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_retrieval_relevant = 1 AND failure_category = 'data_loss_sync' THEN 1 ELSE 0 END)
        FROM feedback_records
    """) as cursor:
        cov_row = await cursor.fetchone()
        relevant_complaints = cov_row[0] or 0
        vague_memory_complaints = cov_row[1] or 0
        data_loss_complaints = cov_row[2] or 0
        
    return {
        "total_corpus": sum(source_counts.values()),
        "source_counts": source_counts,
        "relevant_complaints": relevant_complaints,
        "vague_memory_complaints": vague_memory_complaints,
        "data_loss_complaints": data_loss_complaints
    }

@router.get("/analytics/breakdowns")
async def get_analytics_breakdowns(request: Request):
    """Read-only counts from the validated in-scope database records."""
    pool = await _get_active_pool(request)
    async with pool.execute(f"SELECT count(*) FROM feedback_records WHERE {IN_SCOPE_SQL}") as cursor:
        denominator = (await cursor.fetchone())[0]
    async with pool.execute(f"""
        SELECT CASE WHEN source IS NULL OR trim(source) = '' THEN ? ELSE source END AS source,
               cluster_id, count(*) AS count
        FROM feedback_records WHERE {IN_SCOPE_SQL}
        GROUP BY 1, cluster_id ORDER BY 1, cluster_id
    """, (UNATTRIBUTED_SOURCE,)) as cursor:
        source_cluster = [dict(row) for row in await cursor.fetchall()]
    async with pool.execute(f"""
        SELECT coalesce(nullif(trim(search_strategy), ''), ?) AS value, count(*) AS count
        FROM feedback_records WHERE {IN_SCOPE_SQL}
        GROUP BY 1 ORDER BY count DESC, value
    """, (UNSPECIFIED_STRATEGY,)) as cursor:
        strategies = [dict(row) for row in await cursor.fetchall()]
    async with pool.execute(f"""
        SELECT {WORKAROUND_GROUP_SQL} AS value, count(*) AS count
        FROM feedback_records WHERE {IN_SCOPE_SQL}
        GROUP BY 1 ORDER BY count DESC, value
    """) as cursor:
        workarounds = [dict(row) for row in await cursor.fetchall()]
    return {
        "scope": "in_scope",
        "denominator": denominator,
        "source_cluster": source_cluster,
        "strategies": strategies,
        "workarounds": workarounds,
    }

@router.get("/synthesis")
async def get_synthesis(request: Request):
    """Returns all AI-synthesized strategic Q&A pairs from database."""
    pool = await _get_active_pool(request)
    try:
        async with pool.execute("""
            SELECT question_id, question_text, answer_text, evidence
            FROM synthesis_answers ORDER BY question_id ASC
        """) as cursor:
            rows = await cursor.fetchall()
    except Exception as exc:
        logger.exception("Failed to load saved synthesis")
        raise HTTPException(status_code=503, detail="Saved synthesis is unavailable.") from exc
    res = []
    for row in rows:
        item = dict(row)
        try:
            item["evidence"] = json.loads(item["evidence"])
        except (TypeError, ValueError):
            pass
        res.append(item)
    return {"synthesis": res}

@router.post("/test-search")
async def test_search(request: Request, query_data: SearchQuery):
    """
    Semantic search endpoint for user complaints.
    1. Embeds the user's query using Gemini (or falls back gracefully).
    2. Computes cosine distance against cluster centroids in NumPy.
    3. Computes cosine distance against feedback_records in NumPy.
    4. Gated by calibrated similarity threshold.
    """
    import numpy as np
    pool = await _get_active_pool(request)
        
    SIMILARITY_THRESHOLD = 0.45

    # Attempt embedding with Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    query_embedding = None
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="gemini-embedding-2",
                contents=query_data.query
            )
            if response and response.embeddings:
                query_embedding = response.embeddings[0].values
        except Exception as e:
            logger.warning(f"Gemini embed_content failed: {e}")

    # If embedding failed or no key, fall back to mock search response
    if not query_embedding:
        logger.info("Using mock/lexical fallback for complaint search")
        from api.mock_data import mock_search_response
        response = mock_search_response(query_data.query)
        response["synthetic_fallback"] = True
        response["evidence_notice"] = "Illustrative classifier output; similar records here are synthetic, not retrieved evidence."
        return response

    try:
        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = float(np.linalg.norm(q_vec))
        if q_norm < 1e-9:
            q_norm = 1.0

        # 2. Find Closest Cluster (Cosine Distance via NumPy)
        async with pool.execute("SELECT cluster_id, label, description, severity_score, centroid FROM clusters WHERE centroid IS NOT NULL") as cursor:
            cluster_rows = await cursor.fetchall()

        nearest_cluster = None
        min_cluster_dist = float("inf")
        for r in cluster_rows:
            c_dict = dict(r)
            centroid_blob = c_dict.pop("centroid", None)
            if centroid_blob:
                c_vec = np.frombuffer(centroid_blob, dtype=np.float32)
                c_norm = float(np.linalg.norm(c_vec))
                sim = float(np.dot(q_vec, c_vec)) / max(q_norm * c_norm, 1e-9)
                dist = max(0.0, 1.0 - sim)
                if dist < min_cluster_dist:
                    min_cluster_dist = dist
                    c_dict["distance"] = round(dist, 4)
                    nearest_cluster = c_dict

        if nearest_cluster:
            min_dist = nearest_cluster.get("distance", 1.0)
            if nearest_cluster.get("cluster_id") == 0 and min_dist <= 0.55:
                match_status = "Out of scope: data loss"
            elif min_dist <= SIMILARITY_THRESHOLD:
                match_status = "Confident Match"
            elif min_dist <= 0.55:
                match_status = "Possible match"
            else:
                match_status = "Out-of-domain"
        else:
            match_status = "Out-of-domain"

        # 3. Find Top 5 Similar Records (Cosine Distance via NumPy)
        async with pool.execute("SELECT id, cluster_id, source, source_platform, raw_text, remembered_attributes, forgotten_attributes, search_strategy, failure_point, workaround, emotional_signal, embedding FROM feedback_records WHERE embedding IS NOT NULL") as cursor:
            records_rows = await cursor.fetchall()

        records_with_dist = []
        missing_source_count = 0
        for r in records_rows:
            item = dict(r)
            emb_blob = item.pop("embedding", None)
            if emb_blob:
                r_vec = np.frombuffer(emb_blob, dtype=np.float32)
                r_norm = float(np.linalg.norm(r_vec))
                sim = float(np.dot(q_vec, r_vec)) / max(q_norm * r_norm, 1e-9)
                dist = max(0.0, 1.0 - sim)
                item["distance"] = round(dist, 4)
                item["is_confident"] = bool(dist <= SIMILARITY_THRESHOLD)
                
                canonical_src = item.get("source") or canonicalize_source(item.get("source_platform"))
                if not canonical_src:
                    missing_source_count += 1
                    logger.warning(f"[Missing Source] Nearest complaint record #{item['id']} has no source platform (raw='{item.get('source_platform')}'). Flagged for backfill.")
                item["source"] = canonical_src
                records_with_dist.append(item)

        records_with_dist.sort(key=lambda x: x["distance"])
        similar_records = records_with_dist[:5]

        if missing_source_count > 0:
            logger.warning(f"Total candidate complaints evaluated missing source: {missing_source_count}")

        return {
            "query": query_data.query,
            "match_status": match_status,
            "threshold": SIMILARITY_THRESHOLD,
            "nearest_cluster": nearest_cluster,
            "similar_records": similar_records,
            "synthetic_fallback": False,
        }
            
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        from api.mock_data import mock_search_response
        response = mock_search_response(query_data.query)
        response["synthetic_fallback"] = True
        response["evidence_notice"] = "Illustrative classifier output; similar records here are synthetic, not retrieved evidence."
        return response


@router.get("/pipeline-funnel")
async def get_pipeline_funnel(request: Request):
    """
    Returns pipeline diagnostic funnel data:
    Raw Ingested -> Evaluated by LLM -> Passed Relevance -> Extracted -> Embedded -> Clustered -> Breakdown.
    """
    await _get_active_pool(request)
    from scripts.pipeline_funnel_diagnostic import get_funnel_data
    return get_funnel_data()

@router.get("/evidence")
async def get_evidence(
    request: Request,
    page: int = 1,
    limit: int = 25,
    search: str | None = None,
    source: str | None = None,
    cluster_id: int | None = None,
    emotion: str | None = None,
    search_strategy: str | None = None,
    workaround_group: Literal["no_text", "scroll_mention", "other_text"] | None = None,
    scope: Literal["all", "in_scope", "data_loss", "other_relevant", "irrelevant"] = "all",
):
    """
    Returns paginated scraped evidence records from the full 12,000+ dataset,
    modeled after the Myntra Discovery Engine Evidence Explorer.
    """
    pool = await _get_active_pool(request)
    limit = max(1, min(100, limit))
    page = max(1, page)
    offset = (page - 1) * limit

    conditions = []
    params = []

    if search:
        conditions.append("(raw_text LIKE ? OR failure_point LIKE ? OR photo_type LIKE ?)")
        search_param = f"%{search.strip()}%"
        params.extend([search_param, search_param, search_param])

    if source == UNATTRIBUTED_SOURCE:
        conditions.append("(source IS NULL OR trim(source) = '')")
    elif source and source.lower() != "all":
        conditions.append("source = ?")
        params.append(source)

    if cluster_id is not None:
        conditions.append("cluster_id = ?")
        params.append(cluster_id)

    if emotion and emotion.lower() != "all":
        conditions.append("emotional_signal = ?")
        params.append(emotion.lower())

    if search_strategy == UNSPECIFIED_STRATEGY:
        conditions.append("(search_strategy IS NULL OR trim(search_strategy) = '')")
    elif search_strategy:
        conditions.append("trim(search_strategy) = ?")
        params.append(search_strategy)

    if workaround_group:
        conditions.append(f"({WORKAROUND_GROUP_SQL}) = ?")
        params.append(workaround_group)

    if scope == "in_scope":
        conditions.append("is_retrieval_relevant = 1 AND failure_category = ?")
        params.append("vague_memory_retrieval")
    elif scope == "data_loss":
        conditions.append("is_retrieval_relevant = 1 AND failure_category = ?")
        params.append("data_loss_sync")
    elif scope == "other_relevant":
        conditions.append("is_retrieval_relevant = 1 AND failure_category = ?")
        params.append("none_other")
    elif scope == "irrelevant":
        conditions.append("is_retrieval_relevant = 0")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Total matching count
    count_sql = f"SELECT count(*) FROM feedback_records {where_clause}"
    async with pool.execute(count_sql, params) as cursor:
        total = (await cursor.fetchone())[0]

    async with pool.execute("SELECT cluster_id, label FROM clusters") as cursor:
        cluster_names = dict(await cursor.fetchall())

    # Fetch paginated rows
    data_sql = f"""
        SELECT id, source, raw_text, photo_type, search_strategy,
               failure_point, emotional_signal, cluster_id, created_at
        FROM feedback_records
        {where_clause}
        ORDER BY id ASC
        LIMIT ? OFFSET ?
    """
    fetch_params = params + [limit, offset]
    async with pool.execute(data_sql, fetch_params) as cursor:
        rows = [dict(r) for r in await cursor.fetchall()]

    for r in rows:
        r["cluster_name"] = cluster_names.get(r.get("cluster_id"), f"Cluster #{r.get('cluster_id')}")

    # Aggregates across full corpus
    async with pool.execute("SELECT source, count(*) FROM feedback_records GROUP BY source") as cursor:
        source_counts = dict(await cursor.fetchall())

    async with pool.execute("SELECT cluster_id, count(*) FROM feedback_records GROUP BY cluster_id") as cursor:
        cluster_counts = dict(await cursor.fetchall())

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "records": rows,
        "total_corpus": sum(source_counts.values()),
        "source_counts": source_counts,
        "cluster_counts": cluster_counts
    }


@router.get("/evidence/{record_id}")
async def get_evidence_record(request: Request, record_id: int):
    """Return one source record for shareable citation links."""
    pool = await _get_active_pool(request)
    async with pool.execute("""
        SELECT r.id, r.source, r.source_platform, r.url_id, r.raw_text,
               r.photo_type, r.remembered_attributes, r.forgotten_attributes,
               r.search_strategy, r.failure_point, r.workaround,
               r.emotional_signal, r.cluster_id, r.created_at,
               r.is_retrieval_relevant, r.failure_category,
               c.label AS cluster_name
        FROM feedback_records AS r
        LEFT JOIN clusters AS c ON c.cluster_id = r.cluster_id
        WHERE r.id = ?
    """, (record_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence record not found.")
    record = dict(row)
    record["source"] = record.get("source") or canonicalize_source(record.get("source_platform"))
    return {"record": record}


_COPILOT_STOPWORDS = {
    "a", "about", "all", "an", "and", "are", "can", "do", "does", "for",
    "from", "google", "how", "i", "in", "is", "it", "of", "on", "or",
    "photo", "photos", "search", "show", "tell", "the", "their", "there",
    "these", "this", "to", "user", "users", "what", "when", "which", "why",
    "with", "people", "issues", "problem", "problems", "find", "finding",
    "fail", "fails", "failure", "failing",
}


def _copilot_terms(question: str) -> list[str]:
    return list(dict.fromkeys(
        (term[:-1] if term.endswith("s") and len(term) > 4 else term)
        for term in re.findall(r"[a-z0-9]+", question.lower())
        if len(term) >= 3 and term not in _COPILOT_STOPWORDS
    ))[:8]


def _copilot_term_matches(term: str, text: str) -> bool:
    """Avoid substring hits such as 'pie' in 'piece' or 'picture'."""
    return re.search(rf"\b{re.escape(term)}(?:s|es)?\b", text) is not None


def _excerpt(value: str, length: int = 320) -> str:
    clean = " ".join((value or "").split())
    return clean[:length].rstrip() + ("…" if len(clean) > length else "")


def _gemini_copilot_answer(question: str, candidates: list[dict], synthesis: dict | None) -> dict:
    """Optional wording pass. IDs are validated against the retrieved evidence."""
    prompt = {
        "instruction": "Answer only from these records and saved synthesis. Return JSON with answer and citation_ids. If insufficient, return an empty answer. Do not invent facts or IDs.",
        "question": question,
        "records": [{"id": r["id"], "excerpt": r["excerpt"], "cluster_id": r["cluster_id"]} for r in candidates],
        "saved_synthesis": synthesis,
    }
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    result = client.models.generate_content(
        model=os.getenv("COPILOT_GEMINI_MODEL", "gemini-flash-latest"),
        contents=json.dumps(prompt),
        config={"response_mime_type": "application/json"},
    )
    return json.loads(result.text)


@router.post("/copilot")
async def ask_copilot(request: Request, payload: CopilotQuestion):
    """Ground answers in saved synthesis and actual feedback, or abstain."""
    pool = await _get_active_pool(request)
    question = payload.question.strip()
    terms = _copilot_terms(question)
    limitations = [
        "Answers cite only records classified as relevant vague-memory retrieval complaints; other feedback is excluded.",
        "Matches use words in the saved feedback; they may miss related records phrased differently.",
        "These complaints describe reported experiences, not a measured failure rate for all Google Photos users.",
    ]
    if not terms:
        return {"status": "abstained", "answer": "Please ask about a specific retrieval issue or theme in the evidence.", "mode": "none", "citations": [], "limitations": limitations}

    # Search only the existing corpus. Parameterized LIKE terms keep this independent
    # of Gemini availability and of the classifier's embedding algorithm.
    clauses = []
    parameters = []
    for term in terms:
        clauses.append("(lower(raw_text) LIKE ? OR lower(coalesce(failure_point,'')) LIKE ? OR lower(coalesce(search_strategy,'')) LIKE ?)")
        parameters.extend([f"%{term}%"] * 3)
    sql = """SELECT id, source, source_platform, raw_text, failure_point,
                    search_strategy, cluster_id FROM feedback_records
                    WHERE is_retrieval_relevant = 1
                      AND failure_category = 'vague_memory_retrieval'
                      AND (""" + " OR ".join(clauses) + ") LIMIT 2000"
    async with pool.execute(sql, parameters) as cursor:
        records = [dict(row) for row in await cursor.fetchall()]

    scored = []
    minimum_matches = 2 if len(terms) >= 2 else 1
    for record in records:
        corpus = " ".join(str(record.get(k) or "") for k in ("raw_text", "failure_point", "search_strategy")).lower()
        matches = sum(1 for term in terms if _copilot_term_matches(term, corpus))
        score = matches * 3 + (3 if question.lower() in corpus else 0)
        if matches >= minimum_matches:
            record["excerpt"] = _excerpt(record["raw_text"])
            record["source"] = record.get("source") or canonicalize_source(record.get("source_platform"))
            scored.append((score, record))
    scored.sort(key=lambda entry: (-entry[0], entry[1]["id"]))
    candidates = [record for _, record in scored[:3]]
    if not candidates:
        return {"status": "abstained", "answer": "I could not find supporting records for that question in the saved corpus.", "mode": "none", "citations": [], "limitations": limitations}

    async with pool.execute("SELECT question_text, answer_text, evidence FROM synthesis_answers") as cursor:
        syntheses = [dict(row) for row in await cursor.fetchall()]
    ranked_synthesis = sorted(
        syntheses,
        key=lambda item: sum(1 for term in terms if term in (item["question_text"] + " " + item["answer_text"]).lower()),
        reverse=True,
    )
    synthesis = None
    if ranked_synthesis:
        top = ranked_synthesis[0]
        if sum(1 for term in terms if term in (top["question_text"] + " " + top["answer_text"]).lower()):
            try:
                cited_clusters = json.loads(top["evidence"] or "{}").get("cited_clusters", [])
            except (TypeError, ValueError):
                cited_clusters = []
            if any(record["cluster_id"] in cited_clusters for record in candidates):
                synthesis = {"question": top["question_text"], "finding": _excerpt(top["answer_text"], 350)}

    citations = [{"id": r["id"], "source": r["source"], "excerpt": r["excerpt"], "cluster_id": r["cluster_id"]} for r in candidates]
    extractive = (
        (f"Saved synthesis finding: {synthesis['finding']}\n\n" if synthesis else "")
        + "Matching feedback: "
        + " ".join(f"[{r['id']}] {r['excerpt']}" for r in candidates[:2])
    )
    response = {"status": "answered", "answer": extractive, "mode": "extractive", "citations": citations, "limitations": limitations}

    if os.getenv("COPILOT_USE_GEMINI", "").lower() == "true" and os.getenv("GEMINI_API_KEY"):
        try:
            generated = await asyncio.to_thread(_gemini_copilot_answer, question, candidates, synthesis)
            valid_ids = {r["id"] for r in candidates}
            chosen = generated.get("citation_ids", [])
            if isinstance(generated.get("answer"), str) and generated["answer"].strip() and isinstance(chosen, list) and chosen and all(type(value) is int and value in valid_ids for value in chosen):
                response["answer"] = generated["answer"].strip()
                response["mode"] = "gemini"
                response["citations"] = [citation for citation in citations if citation["id"] in chosen]
        except Exception as exc:
            logger.warning("Copilot wording unavailable; using cited extractive answer: %s", exc)
    return response
