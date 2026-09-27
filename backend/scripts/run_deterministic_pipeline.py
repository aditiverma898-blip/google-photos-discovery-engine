import os
import sys
import glob
import json
import re
import sqlite3
import hashlib
import time
from collections import Counter, defaultdict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Regex patterns for deterministic classification (Offline / Zero-API)
RE_C0 = re.compile(r'\b(miss|lost|disappear|gone|vanish|delet|album|locked folder|trash|bin|recover|cloud|backup.*fail|wiped|erase|cant find photo|disappeared)\w*', re.I)
RE_C1 = re.compile(r'\b(search|find|query|face|people|person|pet|dog|cat|keyword|tag|lens|filter|match|result|who|where|look.*for|cant find|cannot find)\w*', re.I)
RE_C2 = re.compile(r'\b(recent|timeline|date|chronolog|yesterday|today|order|sort|whatsapp|download|screenshot|new photo|newly|upload|time|scrolling|organized)\w*', re.I)
RE_C3 = re.compile(r'\b(ui|update|redesign|layout|grid|scroll|interface|tab|view|button|navigat|mess|terrible|hate|ruin|version|awful|confusing)\w*', re.I)

RE_SCREENSHOT = re.compile(r'\b(screenshot|screen grab|screen capture)\b', re.I)
RE_DOC = re.compile(r'\b(document|pdf|receipt|bill|text|paper|id card|passport|tax|note)\b', re.I)
RE_PET = re.compile(r'\b(dog|cat|pet|puppy|kitten|animal)\b', re.I)
RE_FAMILY = re.compile(r'\b(family|wedding|birthday|baby|kids|children|mom|dad|sister|brother|party|holiday|childhood)\b', re.I)
RE_VACATION = re.compile(r'\b(trip|vacation|travel|beach|mountain|paris|tokyo|tour|flight|hotel|years ago|old photo)\b', re.I)
RE_SELFIE = re.compile(r'\b(selfie|portrait|my face|front camera)\b', re.I)

RE_ANGRY = re.compile(r'\b(worst|terrible|hate|useless|horrible|angry|furious|trash|garbage|disaster|ruined|fraud|scam)\b', re.I)
RE_FRUSTRATED = re.compile(r'\b(frustrat|annoy|irritat|cant even|why is it|broken|waste of time|hard to|difficult|ridiculous|sucks)\b', re.I)
RE_DISAPPOINTED = re.compile(r'\b(disappoint|sad|miss the old|used to be good|poor|regret|unhappy)\b', re.I)

def classify_record(text: str, source: str) -> dict:
    # Cluster assignment
    s0 = len(RE_C0.findall(text))
    s1 = len(RE_C1.findall(text))
    s2 = len(RE_C2.findall(text))
    s3 = len(RE_C3.findall(text))

    scores = [(s1, 1), (s0, 0), (s2, 2), (s3, 3)]
    scores.sort(key=lambda x: x[0], reverse=True)
    best_score, cluster_id = scores[0]
    if best_score == 0:
        cluster_id = 1

    # Photo type
    if RE_SCREENSHOT.search(text):
        photo_type = "screenshot"
    elif RE_DOC.search(text):
        photo_type = "document"
    elif RE_PET.search(text):
        photo_type = "pet"
    elif RE_FAMILY.search(text):
        photo_type = "family_event"
    elif RE_VACATION.search(text):
        photo_type = "old_vacation"
    elif RE_SELFIE.search(text):
        photo_type = "selfie"
    else:
        photo_type = "other"

    # Search strategy
    if "face" in text.lower() or "people" in text.lower() or "person" in text.lower():
        strategy = "people_face_search"
    elif "date" in text.lower() or "year" in text.lower() or "month" in text.lower():
        strategy = "date_filter"
    elif "album" in text.lower() or "folder" in text.lower():
        strategy = "album_browsing"
    elif "scroll" in text.lower() or "timeline" in text.lower():
        strategy = "scrolling_timeline"
    elif "lens" in text.lower():
        strategy = "google_lens"
    elif "search" in text.lower() or "query" in text.lower():
        strategy = "keyword_search"
    else:
        strategy = "keyword_search"

    # Emotional signal
    if RE_ANGRY.search(text):
        emotion = "angry"
    elif RE_FRUSTRATED.search(text):
        emotion = "frustrated"
    elif RE_DISAPPOINTED.search(text):
        emotion = "disappointed"
    else:
        emotion = "neutral"

    # Failure point summary
    if cluster_id == 0:
        failure_point = "Photos or albums missing/vanished from cloud or locked folders"
        remembered = ["album name", "approximate timeframe"]
        forgotten = ["sync status", "exact device folder"]
    elif cluster_id == 1:
        failure_point = "Search query or face/pet tagging yields inaccurate or empty results"
        remembered = ["person or pet name", "scene keywords", "location"]
        forgotten = ["exact date of photo", "original filename"]
    elif cluster_id == 2:
        failure_point = "Recent downloads and uploads displaced into older timeline dates"
        remembered = ["recent download date", "source app (WhatsApp/Camera)"]
        forgotten = ["original EXIF capture date"]
    else:
        failure_point = "UI redesign and navigation changes make finding search and albums confusing"
        remembered = ["old tab navigation layout"]
        forgotten = ["newly moved menu locations"]

    return {
        "cluster_id": cluster_id,
        "photo_type": photo_type,
        "search_strategy": strategy,
        "emotional_signal": emotion,
        "failure_point": failure_point,
        "remembered_attributes": json.dumps(remembered),
        "forgotten_attributes": json.dumps(forgotten),
        "workaround": "Manual scrolling through gallery" if "scroll" in text.lower() else "None reported"
    }

def canonicalize_source(raw_source: str, filepath: str, metadata: dict) -> str:
    s = (raw_source or "").lower()
    store = (metadata.get("store") or "").lower()
    if "youtube" in s or "youtube" in filepath:
        return "YouTube Comment"
    if "reddit" in s or "reddit" in filepath:
        return "Reddit"
    if "help" in s or "forum" in s or "helpforum" in filepath:
        return "Google Support Community"
    if store == "apple_app_store" or "ios" in s or "app_store" in s:
        return "App Store"
    return "Play Store"

def run_deterministic_pipeline():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_dir = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "data", "discovery_engine.db")

    print("=" * 80)
    print("🚀 GOOGLE PHOTOS DISCOVERY ENGINE — OFFLINE DETERMINISTIC PIPELINE")
    print("   Pattern modeled after Myntra Discovery Engine: Zero-API bulk processing")
    print("=" * 80)

    t0 = time.time()
    raw_files = glob.glob(os.path.join(raw_dir, "**", "*.jsonl"), recursive=True)
    print(f"Reading raw data from {len(raw_files)} batch files...")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Pre-fetch existing url_ids
    cur.execute("SELECT url_id FROM feedback_records")
    existing_url_ids = {r[0] for r in cur.fetchall()}
    print(f"Pre-existing records in database: {len(existing_url_ids)}")

    records_to_insert = []
    seen_ids = set(existing_url_ids)
    source_counter = Counter()
    cluster_counter = Counter()
    cluster_quotes = defaultdict(list)

    total_scanned = 0
    for rf in raw_files:
        with open(rf, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total_scanned += 1
                try:
                    obj = json.loads(line)
                    raw_text = (obj.get("raw_text") or obj.get("text") or "").strip()
                    if not raw_text or len(raw_text) < 15:
                        continue

                    source = canonicalize_source(
                        obj.get("source") or obj.get("source_platform"),
                        rf,
                        obj.get("metadata", {})
                    )

                    uid = obj.get("url_id") or obj.get("url")
                    if not uid or uid in seen_ids:
                        h = hashlib.md5(f"{source}_{raw_text}".encode("utf-8")).hexdigest()[:16]
                        uid = f"{source.lower().replace(' ', '_')}_{h}"

                    if uid in seen_ids:
                        continue
                    seen_ids.add(uid)

                    clf = classify_record(raw_text, source)
                    cid = clf["cluster_id"]

                    records_to_insert.append((
                        source.lower().replace(" ", "_"),
                        uid,
                        raw_text,
                        clf["photo_type"],
                        clf["remembered_attributes"],
                        clf["forgotten_attributes"],
                        clf["search_strategy"],
                        clf["failure_point"],
                        clf["workaround"],
                        clf["emotional_signal"],
                        cid,
                        source
                    ))

                    source_counter[source] += 1
                    cluster_counter[cid] += 1

                    # Save candidates for balanced representative quotes
                    if len(cluster_quotes[(cid, source)]) < 5 and 40 < len(raw_text) < 250:
                        cluster_quotes[(cid, source)].append({
                            "quote": raw_text,
                            "source": source
                        })

                except Exception:
                    continue

    print(f"Scanned {total_scanned:,} raw lines in {time.time()-t0:.2f}s.")
    print(f"New valid structured records to insert: {len(records_to_insert):,}")

    if records_to_insert:
        insert_query = """
        INSERT INTO feedback_records (
            source_platform, url_id, raw_text, photo_type,
            remembered_attributes, forgotten_attributes,
            search_strategy, failure_point, workaround,
            emotional_signal, cluster_id, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (url_id) DO UPDATE SET
            cluster_id = excluded.cluster_id,
            source = excluded.source
        """
        cur.executemany(insert_query, records_to_insert)
        conn.commit()
        print("Database bulk insert completed successfully!")

    # Verify total feedback_records
    cur.execute("SELECT count(*) FROM feedback_records")
    total_db = cur.fetchone()[0]
    print(f"\n📊 Total records in feedback_records now: {total_db:,}")

    # Update Cluster Table metadata with real counts and representative quotes
    cur.execute("SELECT cluster_id, count(*) FROM feedback_records GROUP BY cluster_id")
    final_cluster_counts = dict(cur.fetchall())

    cluster_definitions = [
        (0, "Missing Photos and Albums", 
         "Users report missing cloud photos, albums, and locked folder contents after updates or resets, making it difficult to find and organize their media."),
        (1, "Broken Photo Search Functionality", 
         "Users report that searching for recent uploads, specific objects, faces, or keywords frequently yields inaccurate results or fails completely."),
        (2, "Difficulty locating recently added media", 
         "Users struggle to find recently uploaded, downloaded, or backed-up photos and videos when their chronological capture dates are from years ago or when timeline organization makes them hard to spot."),
        (3, "Frustrating UI and Search Redesign", 
         "Users struggle to find and view photos due to difficult scrolling, missing search features, intrusive AI updates, and confusing folder layouts.")
    ]

    for cid, label, desc in cluster_definitions:
        cnt = final_cluster_counts.get(cid, 0)
        
        # Calculate source diversity for this cluster
        cur.execute("SELECT source, count(*) FROM feedback_records WHERE cluster_id = ? GROUP BY source", (cid,))
        s_dist = dict(cur.fetchall())
        tot_c = sum(s_dist.values()) or 1
        source_div = {s: round((c / tot_c) * 100, 1) for s, c in s_dist.items()}

        # Gather balanced quotes across sources
        quotes = []
        for src_name in ["Play Store", "YouTube Comment", "Reddit", "App Store", "Google Support Community"]:
            # Pick from memory or query
            cur.execute("""
                SELECT raw_text, source FROM feedback_records 
                WHERE cluster_id = ? AND source = ? AND length(raw_text) BETWEEN 40 AND 250
                LIMIT 2
            """, (cid, src_name))
            for row in cur.fetchall():
                quotes.append({"quote": row[0], "source": row[1]})

        if len(quotes) < 4:
            # fill with any good quotes from cluster
            cur.execute("""
                SELECT raw_text, source FROM feedback_records 
                WHERE cluster_id = ? AND length(raw_text) BETWEEN 40 AND 250
                LIMIT ?
            """, (cid, 8 - len(quotes)))
            for row in cur.fetchall():
                quotes.append({"quote": row[0], "source": row[1]})

        cur.execute("""
            UPDATE clusters 
            SET record_count = ?,
                source_diversity = ?,
                representative_quotes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE cluster_id = ?
        """, (cnt, json.dumps(source_div), json.dumps(quotes), cid))

    conn.commit()
    conn.close()

    print("\n✅ CLUSTER METADATA SYNCHRONIZED:")
    for cid, label, _ in cluster_definitions:
        print(f"   • Cluster #{cid}: {label:42} -> {final_cluster_counts.get(cid, 0):,}")

    print("\n🎉 Full 12k+ scraped dataset is now live inside the Discovery Engine!")

if __name__ == "__main__":
    run_deterministic_pipeline()
