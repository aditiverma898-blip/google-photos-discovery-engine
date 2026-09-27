import os
import json
import glob
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

# Deterministic Regex Patterns
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

def classify_record(text: str) -> dict:
    """Classifies a raw text record deterministically using heuristics."""
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
    text_lower = text.lower()
    if "face" in text_lower or "people" in text_lower or "person" in text_lower:
        strategy = "people_face_search"
    elif "date" in text_lower or "year" in text_lower or "month" in text_lower:
        strategy = "date_filter"
    elif "album" in text_lower or "folder" in text_lower:
        strategy = "album_browsing"
    elif "scroll" in text_lower or "timeline" in text_lower:
        strategy = "scrolling_timeline"
    elif "lens" in text_lower:
        strategy = "google_lens"
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
        "photo_type": photo_type,
        "search_strategy": strategy,
        "emotional_signal": emotion,
        "failure_point": failure_point,
        "remembered_attributes": remembered,
        "forgotten_attributes": forgotten,
        "workaround": "Manual scrolling through gallery" if "scroll" in text_lower else ""
    }

async def process_raw_data(raw_data_dir: str, limit: int = None, existing_ids: set = None) -> list[dict]:
    """
    Reads .jsonl files in raw_data_dir, extracts structured data deterministically 
    using native regex heuristics (Zero-API / Zero-cost).
    Samples evenly across all sources.
    """
    seen_urls = set(existing_ids or [])
    sources = ["youtube", "reddit", "helpforum", "appstore"]
    records_by_source = {s: [] for s in sources}
    
    for s in sources:
        s_dir = os.path.join(raw_data_dir, s)
        files = glob.glob(os.path.join(s_dir, "**", "*.jsonl"), recursive=True)
        for filepath in files:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            uid = rec.get("url_id") or rec.get("url")
                            if uid and uid not in seen_urls:
                                records_by_source[s].append(rec)
                                seen_urls.add(uid)
                        except Exception:
                            continue

    # Round-robin interleave to guarantee source diversity
    raw_records = []
    max_len = max(len(records_by_source[s]) for s in sources) if any(records_by_source.values()) else 0
    for idx in range(max_len):
        for s in sources:
            if idx < len(records_by_source[s]):
                raw_records.append(records_by_source[s][idx])
                if limit and len(raw_records) >= limit:
                     break
        if limit and len(raw_records) >= limit:
            break
                    
    logger.info(f"Loaded {len(raw_records)} unprocessed raw records across sources for deterministic extraction.")
    if not raw_records:
        return []

    all_extracted = []
    
    for rec in raw_records:
        raw_text = (rec.get("raw_text") or rec.get("text") or "").strip()
        if not raw_text or len(raw_text) < 15:
            continue
            
        platform = rec.get("source_platform") or rec.get("source", "play_store")
        if platform in ("appstore", "google_play", "playstore"):
            platform = "play_store"
        elif platform in ("helpforum", "support", "google_support"):
            platform = "help_community"
        elif platform not in ("reddit", "play_store", "app_store", "help_community", "youtube", "social"):
            platform = "play_store"
            
        url_id = rec.get("url_id") or rec.get("url") or str(hash(raw_text))
        
        # Apply deterministic classification
        classified = classify_record(raw_text)
        
        extracted_record = {
            "source_platform": platform,
            "url_id": url_id,
            "raw_text": raw_text,
            "photo_type": classified["photo_type"],
            "remembered_attributes": classified["remembered_attributes"],
            "forgotten_attributes": classified["forgotten_attributes"],
            "search_strategy": classified["search_strategy"],
            "failure_point": classified["failure_point"],
            "workaround": classified["workaround"],
            "emotional_signal": classified["emotional_signal"]
        }
        all_extracted.append(extracted_record)

    logger.info(f"[extraction] Deterministic processing complete. Extracted {len(all_extracted)} records successfully.")
    
    return all_extracted
