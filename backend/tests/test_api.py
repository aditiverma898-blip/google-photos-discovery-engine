"""API contract tests against a temporary dataset, never the committed corpus."""

import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.main import app, FRONTEND_DIST
from db import connection


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    path = tmp_path / "evidence.db"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE feedback_records (
            id INTEGER PRIMARY KEY, source TEXT, source_platform TEXT, url_id TEXT,
            raw_text TEXT, photo_type TEXT, remembered_attributes TEXT,
            forgotten_attributes TEXT, search_strategy TEXT, failure_point TEXT,
            workaround TEXT, emotional_signal TEXT, cluster_id INTEGER,
            created_at TEXT, is_retrieval_relevant INTEGER, failure_category TEXT,
            classification_confidence REAL, embedding BLOB);
        CREATE TABLE clusters (
            cluster_id INTEGER PRIMARY KEY, label TEXT, description TEXT,
            severity_score REAL, top_failure_points TEXT, centroid BLOB);
        CREATE TABLE synthesis_answers (
            question_id INTEGER PRIMARY KEY, question_text TEXT,
            answer_text TEXT, evidence TEXT);
        INSERT INTO clusters VALUES
            (1, 'Background recall', 'Secondary objects are hard to find', 0.8, '[]', NULL),
            (2, 'Time recall', 'Relative time is hard to find', 0.6, '[]', NULL);
        INSERT INTO feedback_records VALUES
            (1, 'Reddit', 'reddit', 'r/1', 'The blue truck in the background never appears in search.',
             'photo', 'truck', NULL, 'blue truck', 'background object not indexed', NULL,
             'frustrated', 1, '2026-01-01', 1, 'vague_memory_retrieval', 0.9, NULL),
            (2, 'Play Store', 'play_store', 'p/2', 'I cannot find a photo from after my birthday.',
             'photo', 'birthday', NULL, 'after birthday', 'relative time search fails', NULL,
             'frustrated', 2, '2026-01-02', 1, 'vague_memory_retrieval', 0.8, NULL),
            (3, 'Reddit', 'reddit', 'r/3', 'Searching for the red car in the background returns nothing.',
             'photo', 'car', NULL, 'red car', 'background object not indexed', NULL,
             'confused', 1, '2026-01-03', 1, 'vague_memory_retrieval', 0.7, NULL);
        INSERT INTO synthesis_answers VALUES
            (1, 'Why do background objects cause search trouble?',
             'Background objects are often not indexed as searchable concepts.',
             '{"cited_clusters":[1]}');
    """)
    db.close()
    monkeypatch.setattr(connection, "DB_PATH", str(path))
    app.state.pool = None
    return path


async def _close():
    await connection.close_read_only_pool()
    app.state.pool = None


@pytest.mark.asyncio
async def test_read_only_cold_start_and_current_routes(dataset):
    before = hashlib.sha256(dataset.read_bytes()).hexdigest()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/coverage")).json()["total_corpus"] == 3
            assert len((await client.get("/api/clusters")).json()["clusters"]) == 2
            assert len((await client.get("/api/synthesis")).json()["synthesis"]) == 1
            evidence = (await client.get("/api/evidence?source=Reddit&limit=1&page=2")).json()
            assert evidence["total"] == 2
            assert evidence["records"][0]["id"] == 3
        assert hashlib.sha256(dataset.read_bytes()).hexdigest() == before
    finally:
        await _close()


@pytest.mark.asyncio
async def test_evidence_deep_link_and_missing_record(dataset):
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/evidence/1")
            assert response.status_code == 200
            assert response.json()["record"]["cluster_name"] == "Background recall"
            assert response.json()["record"]["raw_text"].startswith("The blue truck")
            assert (await client.get("/api/evidence/999")).status_code == 404
    finally:
        await _close()


@pytest.mark.asyncio
async def test_evidence_scope_filters_and_combines_with_cluster(dataset):
    db = sqlite3.connect(dataset)
    db.executemany("""
        INSERT INTO feedback_records
            (id, source, raw_text, cluster_id, is_retrieval_relevant, failure_category)
        VALUES (?, 'Reddit', ?, 1, ?, ?)
    """, [
        (4, "Photos disappeared during sync", 1, "data_loss_sync"),
        (5, "A different relevant issue", 1, "none_other"),
        (6, "General app feedback", 0, "vague_memory_retrieval"),
        (7, "Classification pending", None, None),
    ])
    db.commit()
    db.close()
    expected = {
        "all": (7, [1, 2, 3, 4, 5, 6, 7]),
        "in_scope": (3, [1, 2, 3]),
        "data_loss": (1, [4]),
        "other_relevant": (1, [5]),
        "irrelevant": (1, [6]),
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for scope, (count, ids) in expected.items():
                response = await client.get("/api/evidence", params={"scope": scope})
                assert response.status_code == 200
                assert response.json()["total"] == count
                assert [row["id"] for row in response.json()["records"]] == ids
            combined = (await client.get("/api/evidence", params={"scope": "in_scope", "cluster_id": 1})).json()
            assert combined["total"] == 2
            assert [row["id"] for row in combined["records"]] == [1, 3]
            assert (await client.get("/api/evidence?scope=unknown")).status_code == 422
            assert (await client.get("/api/evidence")).json()["total"] == 7
    finally:
        await _close()


@pytest.mark.asyncio
async def test_breakdowns_reconcile_and_open_matching_evidence(dataset):
    db = sqlite3.connect(dataset)
    db.executemany("""
        INSERT INTO feedback_records
            (id, source, raw_text, cluster_id, is_retrieval_relevant,
             failure_category, search_strategy, workaround)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (4, None, "I scrolled through years of photos", 1, 1, "vague_memory_retrieval", "keyword_search", "manual scrolling"),
        (5, "Reddit", "Date search failed", 2, 1, "vague_memory_retrieval", "keyword_search", "none"),
        (6, "Reddit", "Unrelated app feedback", 1, 0, "none_other", "keyword_search", "manual scrolling"),
        (7, "Play Store", "I gave up looking", 2, 1, "vague_memory_retrieval", "album_browsing", "gave up"),
    ])
    db.commit()
    db.close()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/analytics/breakdowns")
            assert response.status_code == 200
            data = response.json()
            assert data["denominator"] == 6
            assert sum(row["count"] for row in data["source_cluster"]) == 6
            assert sum(row["count"] for row in data["strategies"]) == 6
            assert sum(row["count"] for row in data["workarounds"]) == 6
            assert {row["value"]: row["count"] for row in data["workarounds"]} == {
                "no_text": 4, "scroll_mention": 1, "other_text": 1,
            }
            for row in data["source_cluster"]:
                result = (await client.get("/api/evidence", params={
                    "scope": "in_scope", "source": row["source"], "cluster_id": row["cluster_id"],
                })).json()
                assert result["total"] == row["count"]
            for row in data["strategies"]:
                result = (await client.get("/api/evidence", params={
                    "scope": "in_scope", "search_strategy": row["value"],
                })).json()
                assert result["total"] == row["count"]
            for row in data["workarounds"]:
                result = (await client.get("/api/evidence", params={
                    "scope": "in_scope", "workaround_group": row["value"],
                })).json()
                assert result["total"] == row["count"]
            assert (await client.get("/api/evidence?workaround_group=invalid")).status_code == 422
    finally:
        await _close()


@pytest.mark.asyncio
async def test_copilot_cites_existing_ids_abstains_and_skips_gemini(dataset, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unused-test-key")
    monkeypatch.delenv("COPILOT_USE_GEMINI", raising=False)
    monkeypatch.setattr("api.routes._gemini_copilot_answer", lambda *args: pytest.fail("Gemini must be disabled"))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = (await client.post("/api/copilot", json={"question": "Why do background objects fail?"})).json()
            assert response["status"] == "answered"
            assert response["mode"] == "extractive"
            assert {c["id"] for c in response["citations"]} <= {1, 3}
            assert response["limitations"]
            assert "Saved synthesis" in response["answer"]
            empty = (await client.post("/api/copilot", json={"question": "purple kangaroo nebula"})).json()
            assert empty["status"] == "abstained"
            assert empty["citations"] == []
    finally:
        await _close()


@pytest.mark.asyncio
async def test_copilot_excludes_out_of_scope_evidence(dataset, monkeypatch):
    db = sqlite3.connect(dataset)
    db.executemany("""
        INSERT INTO feedback_records
            (id, source, raw_text, cluster_id, is_retrieval_relevant, failure_category)
        VALUES (?, 'Reddit', ?, 1, ?, ?)
    """, [
        (4, "Background objects background objects background objects disappeared in sync", 1, "data_loss_sync"),
        (5, "Background objects background objects background objects: general app feedback", 0, "none_other"),
        (6, "Background objects background objects background objects: other relevant issue", 1, "none_other"),
    ])
    db.commit()
    db.close()
    monkeypatch.delenv("COPILOT_USE_GEMINI", raising=False)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = (await client.post("/api/copilot", json={"question": "background objects"})).json()
            assert response["status"] == "answered"
            assert {citation["id"] for citation in response["citations"]} <= {1, 3}
            assert "vague-memory retrieval" in " ".join(response["limitations"])
    finally:
        await _close()


@pytest.mark.asyncio
async def test_copilot_abstains_on_unrelated_or_single_weak_term(dataset):
    db = sqlite3.connect(dataset)
    db.execute("""
        INSERT INTO feedback_records
            (id, source, raw_text, cluster_id, is_retrieval_relevant, failure_category)
        VALUES (4, 'Reddit', 'A picture of a piece of paper never appears in search',
                1, 1, 'vague_memory_retrieval')
    """)
    db.execute("""
        INSERT INTO feedback_records
            (id, source, raw_text, cluster_id, is_retrieval_relevant, failure_category)
        VALUES (5, 'Reddit', 'I remember a blue truck in the background but cannot retrieve it',
                1, 1, 'vague_memory_retrieval')
    """)
    db.commit()
    db.close()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for question in ("How do I bake a cherry pie?", "birthday flamingo"):
                response = (await client.post("/api/copilot", json={"question": question})).json()
                assert response["status"] == "abstained"
                assert response["citations"] == []
            valid = (await client.post("/api/copilot", json={"question": "What do people remember about a photo?"})).json()
            assert valid["status"] == "answered"
            assert [citation["id"] for citation in valid["citations"]] == [5]
    finally:
        await _close()


@pytest.mark.asyncio
async def test_copilot_rejects_gemini_citations_outside_retrieval(dataset, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unused-test-key")
    monkeypatch.setenv("COPILOT_USE_GEMINI", "true")
    monkeypatch.setattr("api.routes._gemini_copilot_answer", lambda *args: {"answer": "Unsupported claim", "citation_ids": [999]})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = (await client.post("/api/copilot", json={"question": "background objects"})).json()
            assert response["mode"] == "extractive"
            assert "Unsupported claim" not in response["answer"]
            assert {c["id"] for c in response["citations"]} <= {1, 3}
    finally:
        await _close()


@pytest.mark.asyncio
async def test_classifier_synthetic_fallback_is_labeled(dataset, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = (await client.post("/api/test-search", json={"query": "blue truck"})).json()
            assert response["synthetic_fallback"] is True
            assert "synthetic" in response["evidence_notice"].lower()
            assert response["threshold"] == 0.45
    finally:
        await _close()


@pytest.mark.asyncio
async def test_missing_database_is_explicit_error(tmp_path, monkeypatch):
    missing = tmp_path / "missing.db"
    monkeypatch.setattr(connection, "DB_PATH", str(missing))
    app.state.pool = None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/evidence")).status_code == 503
            assert (await client.get("/api/analytics/breakdowns")).status_code == 503
            assert (await client.post("/api/copilot", json={"question": "background search"})).status_code == 503
        assert not missing.exists()
    finally:
        await _close()


@pytest.mark.asyncio
async def test_built_frontend_deep_links_and_private_data():
    if not (FRONTEND_DIST / "index.html").is_file():
        pytest.skip("Frontend build is required for SPA route verification")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/analytics", "/evidence", "/copilot", "/methodology", "/cluster/1"):
            response = await client.get(path, headers={"Accept": "text/html"})
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
        for path in ("/backend/data/discovery_engine.db", "/backend/data/raw/reddit/2026-09-17/batch_0000.jsonl"):
            response = await client.get(path, headers={"Accept": "application/octet-stream"})
            assert response.status_code == 404
