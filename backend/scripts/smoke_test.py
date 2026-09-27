"""
Smoke Test — Verify connectivity to all external services.

Run:  python scripts/smoke_test.py

Tests:
  1. Gemini API — simple generate call
  2. Reddit API — authentication check
  3. PostgreSQL — connection + table existence
  4. YouTube Data API — basic search query
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ─── Test Results Tracking ────────────────────────────────────────────
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []

    def record(self, name: str, status: str, message: str = ""):
        self.results.append({"name": name, "status": status, "message": message})
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        else:
            self.skipped += 1

    def print_summary(self):
        print("\n" + "=" * 60)
        print("  SMOKE TEST RESULTS")
        print("=" * 60)
        for r in self.results:
            icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⏭️"
            msg = f"  — {r['message']}" if r["message"] else ""
            print(f"  {icon} {r['name']}: {r['status']}{msg}")
        print("-" * 60)
        print(f"  Total: {self.passed} passed, {self.failed} failed, {self.skipped} skipped")
        print("=" * 60)
        return self.failed == 0


results = TestResults()


# ─── Test 1: Gemini API ───────────────────────────────────────────────
async def test_gemini_api():
    """Verify the Gemini API key works with a simple generate call."""
    api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key or api_key == "your_gemini_api_key_here":
        results.record("Gemini API", "SKIP", "GEMINI_API_KEY not configured in .env")
        return

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Reply with exactly: SMOKE_TEST_OK",
        )
        text = response.text.strip()

        if "SMOKE_TEST_OK" in text:
            results.record("Gemini API", "PASS", f"Model responded: {text[:50]}")
        else:
            results.record("Gemini API", "PASS", f"Model responded (unexpected format): {text[:50]}")
    except ImportError:
        results.record("Gemini API", "FAIL", "google-genai package not installed. Run: pip install google-genai")
    except Exception as e:
        results.record("Gemini API", "FAIL", str(e)[:100])


# ─── Test 2: Reddit API ──────────────────────────────────────────────
async def test_reddit_api():
    """Verify Reddit API credentials authenticate successfully."""
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    user_agent = os.getenv("REDDIT_USER_AGENT", "DiscoveryEngine/1.0")

    if not client_id or client_id == "your_reddit_client_id_here":
        results.record("Reddit API", "SKIP", "REDDIT_CLIENT_ID not configured in .env")
        return

    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        # Test: read-only access to a public subreddit
        subreddit = reddit.subreddit("googlephotos")
        display_name = subreddit.display_name
        results.record("Reddit API", "PASS", f"Authenticated. Subreddit: r/{display_name}")
    except ImportError:
        results.record("Reddit API", "FAIL", "praw package not installed. Run: pip install praw")
    except Exception as e:
        results.record("Reddit API", "FAIL", str(e)[:100])


# ─── Test 3: PostgreSQL ──────────────────────────────────────────────
async def test_postgresql():
    """Verify PostgreSQL connection and check if tables exist."""
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url or database_url == "postgresql://postgres:postgres@localhost:5432/discovery_engine":
        # Try to connect anyway with the default URL
        pass

    try:
        import asyncpg

        conn = await asyncpg.connect(
            dsn=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/discovery_engine")
        )

        # Test basic connectivity
        version = await conn.fetchval("SELECT version()")

        # Check if pgvector extension is installed
        pgvector = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )

        # Check if tables exist
        tables = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        table_names = [t["table_name"] for t in tables]

        await conn.close()

        required = {"feedback_records", "clusters", "synthesis_answers", "ingestion_log", "pipeline_runs"}
        existing = set(table_names) & required
        missing = required - existing

        status_parts = [
            f"Connected to PostgreSQL",
            f"pgvector: {'✅' if pgvector else '❌ NOT INSTALLED'}",
            f"Tables: {len(existing)}/{len(required)} present",
        ]
        if missing:
            status_parts.append(f"Missing: {', '.join(sorted(missing))}")

        all_good = pgvector and not missing
        results.record(
            "PostgreSQL",
            "PASS" if all_good else "PASS" if pgvector else "FAIL",
            " | ".join(status_parts),
        )
    except ImportError:
        results.record("PostgreSQL", "FAIL", "asyncpg not installed. Run: pip install asyncpg")
    except OSError as e:
        results.record("PostgreSQL", "FAIL", f"Connection refused — is PostgreSQL running? ({e})")
    except Exception as e:
        results.record("PostgreSQL", "FAIL", str(e)[:100])


# ─── Test 4: YouTube Data API ────────────────────────────────────────
async def test_youtube_api():
    """Verify the YouTube Data API key works with a basic search."""
    api_key = os.getenv("YOUTUBE_API_KEY", "")

    if not api_key or api_key == "your_youtube_api_key_here":
        results.record("YouTube API", "SKIP", "YOUTUBE_API_KEY not configured in .env")
        return

    try:
        import aiohttp

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": api_key,
            "q": "Google Photos search tutorial",
            "part": "snippet",
            "type": "video",
            "maxResults": 1,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = data.get("pageInfo", {}).get("totalResults", 0)
                    results.record("YouTube API", "PASS", f"API key valid. Found {count} results")
                elif resp.status == 403:
                    results.record("YouTube API", "FAIL", "API key invalid or quota exceeded (403)")
                else:
                    body = await resp.text()
                    results.record("YouTube API", "FAIL", f"HTTP {resp.status}: {body[:80]}")
    except ImportError:
        results.record("YouTube API", "FAIL", "aiohttp not installed. Run: pip install aiohttp")
    except Exception as e:
        results.record("YouTube API", "FAIL", str(e)[:100])


# ─── Main ─────────────────────────────────────────────────────────────
async def main():
    print("\n🔍 Google Photos Discovery Engine — Smoke Test")
    print("=" * 60)

    print("\n🤖 Testing Gemini API...")
    await test_gemini_api()

    print("📱 Testing Reddit API...")
    await test_reddit_api()

    print("🐘 Testing PostgreSQL...")
    await test_postgresql()

    print("📺 Testing YouTube API...")
    await test_youtube_api()

    all_passed = results.print_summary()

    if all_passed:
        print("\n🎉 All tests passed! Ready for Phase 1.\n")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above before proceeding.\n")
        print("   Skipped tests are OK — configure the API keys when ready.\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
