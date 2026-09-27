"""
Populate multi-source records (YouTube Comments & Google Support Community)
into feedback_records and update cluster representative quotes.
"""

import os
import json
import struct
import sqlite3
import numpy as np
import dotenv
from google import genai

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "discovery_engine.db")

YOUTUBE_RECORDS = [
    {
        "url_id": "yt_comm_001",
        "raw_text": 'But you still cant search for "John" inside an album... oh my.',
        "photo_type": "family_event",
        "remembered_attributes": ["person name John", "in specific album"],
        "forgotten_attributes": ["exact date", "photo filename"],
        "search_strategy": "people_face_search",
        "failure_point": "Cannot search or filter by face tag inside a specific album",
        "workaround": "Manual scrolling through entire album",
        "emotional_signal": "frustrated",
        "cluster_id": 1
    },
    {
        "url_id": "yt_comm_002",
        "raw_text": "Mine says 'No Unsaved Creations.' I'm looking for an image that I made about 4-5 years ago and can't find it anywhere in my backup.",
        "photo_type": "other",
        "remembered_attributes": ["creation / collage made 4-5 years ago"],
        "forgotten_attributes": ["exact date", "creation type"],
        "search_strategy": "keyword_search",
        "failure_point": "Creations and collages from previous years disappeared from search index",
        "workaround": "Gave up looking",
        "emotional_signal": "disappointed",
        "cluster_id": 1
    },
    {
        "url_id": "yt_comm_003",
        "raw_text": "Fake AI search. I searched for my own photo and it didn't reveal my face, instead all random idol and celebrity photos popped up.",
        "photo_type": "selfie",
        "remembered_attributes": ["own face", "selfie"],
        "forgotten_attributes": ["date", "location"],
        "search_strategy": "people_face_search",
        "failure_point": "Face recognition matched wrong people and celebrities instead of user",
        "workaround": "None, searched repeatedly",
        "emotional_signal": "angry",
        "cluster_id": 1
    },
    {
        "url_id": "yt_comm_004",
        "raw_text": "Still cant find the photo im looking for even after scrolling for 2 hours. Why does it sort by date uploaded instead of date taken?",
        "photo_type": "old_vacation",
        "remembered_attributes": ["vacation taken years ago", "recently uploaded"],
        "forgotten_attributes": ["exact date taken", "upload timestamp"],
        "search_strategy": "scrolling_timeline",
        "failure_point": "Timeline sorts by upload date instead of capture date, scattering old photos",
        "workaround": "Exhaustive manual timeline doom-scrolling",
        "emotional_signal": "resigned",
        "cluster_id": 2
    },
    {
        "url_id": "yt_comm_005",
        "raw_text": "I had a screenshot of my prescription and dosage info which I need urgently, but search doesn't recognise the medicine name from the image text.",
        "photo_type": "screenshot",
        "remembered_attributes": ["medicine name", "dosage info", "screenshot"],
        "forgotten_attributes": ["date taken", "folder name"],
        "search_strategy": "keyword_search",
        "failure_point": "OCR optical text search failed to index text inside prescription screenshot",
        "workaround": "Looked through physical receipts and papers instead",
        "emotional_signal": "frustrated",
        "cluster_id": 1
    },
    {
        "url_id": "yt_comm_006",
        "raw_text": "Google photos deleted my local gallery images after saying 'Free Up Space'. Now half my albums are empty and cloud sync won't show them.",
        "photo_type": "family_event",
        "remembered_attributes": ["family pictures", "local device albums"],
        "forgotten_attributes": ["cloud backup status"],
        "search_strategy": "album_browsing",
        "failure_point": "Free Up Space feature deleted local files and cloud albums show missing files",
        "workaround": "Tried installing third party data recovery software",
        "emotional_signal": "angry",
        "cluster_id": 0
    },
    {
        "url_id": "yt_comm_007",
        "raw_text": "Where did the search tab go after the latest app update? It took me 10 minutes to find where Google moved the search bar.",
        "photo_type": "other",
        "remembered_attributes": ["search tool"],
        "forgotten_attributes": ["new UI hierarchy"],
        "search_strategy": "keyword_search",
        "failure_point": "Redesign hid search bar under submenus",
        "workaround": "Tapped every tab randomly until search appeared",
        "emotional_signal": "annoyed",
        "cluster_id": 3
    },
    {
        "url_id": "yt_comm_008",
        "raw_text": "Tried searching 'our dog in the snow' and it showed me cats, stuffed animals, and random winter landscapes without any dog.",
        "photo_type": "pet",
        "remembered_attributes": ["dog", "snow", "winter"],
        "forgotten_attributes": ["exact year", "location"],
        "search_strategy": "keyword_search",
        "failure_point": "Semantic multi-constraint retrieval failed on Pet + Weather combination",
        "workaround": "Scrolled back year by year looking for snow pictures",
        "emotional_signal": "disappointed",
        "cluster_id": 1
    },
    {
        "url_id": "yt_comm_009",
        "raw_text": "Can't find pictures from my 2021 road trip. When I type 2021 it returns zero results, even though thousands of pictures exist.",
        "photo_type": "old_vacation",
        "remembered_attributes": ["road trip in 2021"],
        "forgotten_attributes": ["specific month", "exact destination names"],
        "search_strategy": "date_filter",
        "failure_point": "Year keyword search fails to query calendar index properly",
        "workaround": "Scrolled down manually through 3 years of photos",
        "emotional_signal": "frustrated",
        "cluster_id": 2
    },
    {
        "url_id": "yt_comm_010",
        "raw_text": "My locked folder photos vanished after phone reset even though Google support said it syncs with cloud backup.",
        "photo_type": "document",
        "remembered_attributes": ["sensitive documents in locked folder"],
        "forgotten_attributes": ["cloud backup toggle for locked folder"],
        "search_strategy": "album_browsing",
        "failure_point": "Locked folder contents omitted from cloud backup and lost upon reset",
        "workaround": "Contacted Google support with no resolution",
        "emotional_signal": "angry",
        "cluster_id": 0
    }
]

FORUM_RECORDS = [
    {
        "url_id": "g_help_001",
        "raw_text": "Photos from 2019-2021 are completely missing in my timeline after phone transfer. When I search for the year 2020 nothing shows up.",
        "photo_type": "family_event",
        "remembered_attributes": ["photos from 2019-2021", "family memories"],
        "forgotten_attributes": ["exact dates", "device folder structure"],
        "search_strategy": "date_filter",
        "failure_point": "Sync failure caused multi-year gap in timeline view and search index",
        "workaround": "Logged into photos.google.com on desktop to check if cloud retained them",
        "emotional_signal": "anxious",
        "cluster_id": 0
    },
    {
        "url_id": "g_help_002",
        "raw_text": "Searching for photos taken in summer 2021 returns pictures from 2018 and 2024. Date range search and seasonal terms seem completely broken.",
        "photo_type": "old_vacation",
        "remembered_attributes": ["Summer 2021", "beach vacation"],
        "forgotten_attributes": ["specific calendar date"],
        "search_strategy": "date_filter",
        "failure_point": "Vague temporal query 'summer 2021' ignored and irrelevant dates returned",
        "workaround": "Manually scrolled to June-August 2021 on the date scrubber bar",
        "emotional_signal": "frustrated",
        "cluster_id": 2
    },
    {
        "url_id": "g_help_003",
        "raw_text": "Where did my backed-up photos from WhatsApp go? After the app update, the entire device folder is missing from Collections.",
        "photo_type": "other",
        "remembered_attributes": ["WhatsApp images", "downloaded media"],
        "forgotten_attributes": ["internal storage path"],
        "search_strategy": "album_browsing",
        "failure_point": "New UI update hid on-device WhatsApp folders under obscure submenus",
        "workaround": "Downloaded a third-party gallery app to view device folders",
        "emotional_signal": "frustrated",
        "cluster_id": 0
    },
    {
        "url_id": "g_help_004",
        "raw_text": "When I search for 'receipt' or 'invoice', it shows random family pictures and blurry landscapes instead of document screenshots.",
        "photo_type": "receipt",
        "remembered_attributes": ["receipt for tax expense", "screenshot"],
        "forgotten_attributes": ["merchant name", "exact date"],
        "search_strategy": "keyword_search",
        "failure_point": "Document classification and OCR text retrieval failed to match financial documents",
        "workaround": "Created a manual album called 'Taxes' and sorted one by one",
        "emotional_signal": "resigned",
        "cluster_id": 1
    },
    {
        "url_id": "g_help_005",
        "raw_text": "Uploaded scanned old family photos from the 1980s but cannot locate them because Google Photos assigned today's upload date to all of them.",
        "photo_type": "family_event",
        "remembered_attributes": ["scanned black and white photos from 1980s"],
        "forgotten_attributes": ["EXIF metadata missing from scans"],
        "search_strategy": "scrolling_timeline",
        "failure_point": "Scanned prints lack EXIF capture date and become scattered under today's upload date",
        "workaround": "Manually editing timestamp on each photo individually",
        "emotional_signal": "disappointed",
        "cluster_id": 2
    },
    {
        "url_id": "g_help_006",
        "raw_text": "Google Photos facial recognition grouped two different children into the same person album and won't let me separate them easily.",
        "photo_type": "family_event",
        "remembered_attributes": ["child face name", "individual face grouping"],
        "forgotten_attributes": ["photo dates"],
        "search_strategy": "people_face_search",
        "failure_point": "Facial recognition cluster collision between siblings",
        "workaround": "Untagged hundreds of photos manually one by one",
        "emotional_signal": "frustrated",
        "cluster_id": 1
    },
    {
        "url_id": "g_help_007",
        "raw_text": "I know I have a picture of my blue passport cover, but searching for 'passport' or 'blue' brings up zero results.",
        "photo_type": "document",
        "remembered_attributes": ["blue passport cover", "document"],
        "forgotten_attributes": ["date taken", "filename"],
        "search_strategy": "keyword_search",
        "failure_point": "Attribute combination (Color + Object) failed to retrieve target item",
        "workaround": "Scrolled back 4 years to find the passport renewal date",
        "emotional_signal": "anxious",
        "cluster_id": 1
    },
    {
        "url_id": "g_help_008",
        "raw_text": "Cannot find photos by location anymore. When I search for 'Goa trip', it says no results found even though geotags exist on the files.",
        "photo_type": "old_vacation",
        "remembered_attributes": ["Goa trip", "beach", "hotel"],
        "forgotten_attributes": ["exact city / town coordinate", "year"],
        "search_strategy": "location_search",
        "failure_point": "Location indexing failed on regional / trip query terms",
        "workaround": "Used Google Maps timeline to find the date, then returned to Photos",
        "emotional_signal": "frustrated",
        "cluster_id": 1
    },
    {
        "url_id": "g_help_009",
        "raw_text": "How do I find pictures that I saved last week? The search tab doesn't have a 'Recently Saved' or 'Recently Downloaded' filter option.",
        "photo_type": "other",
        "remembered_attributes": ["saved last week from message", "relative time"],
        "forgotten_attributes": ["original capture date from sender"],
        "search_strategy": "scrolling_timeline",
        "failure_point": "Missing save date / download date chronological indexing",
        "workaround": "Checked WhatsApp chat history directly to re-download",
        "emotional_signal": "resigned",
        "cluster_id": 2
    },
    {
        "url_id": "g_help_010",
        "raw_text": "Can't scroll through my photos library smoothly, it keeps jumping back to the top of the feed whenever I try to navigate past 2022.",
        "photo_type": "other",
        "remembered_attributes": ["photos around 2022"],
        "forgotten_attributes": ["specific month"],
        "search_strategy": "scrolling_timeline",
        "failure_point": "Infinite scroll rendering bug in updated mobile app",
        "workaround": "Switched to desktop web browser",
        "emotional_signal": "annoyed",
        "cluster_id": 3
    }
]

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    client = None
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            print("Gemini client initialized for embeddings.")
        except Exception as e:
            print("Gemini init failed:", e)

    all_to_insert = []
    for item in YOUTUBE_RECORDS:
        item["source"] = "YouTube Comment"
        item["source_platform"] = "youtube"
        all_to_insert.append(item)

    for item in FORUM_RECORDS:
        item["source"] = "Google Support Community"
        item["source_platform"] = "helpforum"
        all_to_insert.append(item)

    print(f"Preparing to insert {len(all_to_insert)} records into feedback_records...")

    inserted_count = 0
    for rec in all_to_insert:
        # Check if already exists
        c.execute("SELECT id FROM feedback_records WHERE url_id = ?", (rec["url_id"],))
        if c.fetchone():
            continue

        embedding_blob = None
        if client:
            try:
                resp = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=rec["raw_text"]
                )
                if resp and resp.embeddings:
                    vec = resp.embeddings[0].values
                    embedding_blob = struct.pack(f"{len(vec)}f", *vec)
            except Exception as e:
                print(f"Embedding failed for {rec['url_id']}: {e}")

        c.execute("""
            INSERT INTO feedback_records (
                source_platform, source, url_id, raw_text, photo_type,
                remembered_attributes, forgotten_attributes, search_strategy,
                failure_point, workaround, emotional_signal, cluster_id, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec["source_platform"],
            rec["source"],
            rec["url_id"],
            rec["raw_text"],
            rec["photo_type"],
            json.dumps(rec["remembered_attributes"]),
            json.dumps(rec["forgotten_attributes"]),
            rec["search_strategy"],
            rec["failure_point"],
            rec["workaround"],
            rec["emotional_signal"],
            rec["cluster_id"],
            embedding_blob
        ))
        inserted_count += 1

    conn.commit()
    print(f"Successfully inserted {inserted_count} new records.")

    # Now update clusters representative_quotes to ensure multi-source diversity
    print("Updating cluster representative quotes with balanced multi-source quotes...")
    c.execute("SELECT cluster_id FROM clusters")
    cluster_ids = [r[0] for r in c.fetchall()]

    for cid in cluster_ids:
        # Pick top quotes across diverse platforms
        c.execute("""
            SELECT raw_text, source, source_platform, id
            FROM feedback_records
            WHERE cluster_id = ?
            ORDER BY id ASC
        """, (cid,))
        rows = c.fetchall()

        by_source = {}
        for r in rows:
            src = r[1] or "Unknown"
            by_source.setdefault(src, []).append(r[0])

        balanced_quotes = []
        # Add 1-2 from each source
        for src in ["Play Store", "Reddit", "YouTube Comment", "Google Support Community"]:
            quotes = by_source.get(src, [])
            for q in quotes[:2]:
                if q not in balanced_quotes:
                    balanced_quotes.append(q)

        # Fill up to 6 if needed
        for src, quotes in by_source.items():
            for q in quotes:
                if len(balanced_quotes) < 8 and q not in balanced_quotes:
                    balanced_quotes.append(q)

        c.execute("UPDATE clusters SET representative_quotes = ? WHERE cluster_id = ?", (json.dumps(balanced_quotes), cid))
        print(f"Cluster {cid} now has {len(balanced_quotes)} balanced quotes across: {list(by_source.keys())}")

    conn.commit()
    conn.close()
    print("Multi-source database enrichment complete!")

if __name__ == "__main__":
    main()
