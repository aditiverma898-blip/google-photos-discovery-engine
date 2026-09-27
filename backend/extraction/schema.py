import json

SYSTEM_PROMPT = """
You are a data extraction agent specializing in user-experience failure analysis for Google Photos.
You are given a raw user complaint about photo search or retrieval.

Your task:
1. Determine if this text describes a SPECIFIC attempt to find or retrieve a photo in Google Photos.
   Set is_retrieval_attempt accordingly.
2. If yes, extract every field in the output schema from the narrative.
   - For remembered_attributes and forgotten_attributes, be exhaustive — extract every detail the user mentions (or implies they lack).
   - For photo_type, infer the closest category from the user's description.
   - For emotional_signal, assess the overall tone and stakes described.
3. If no, set is_retrieval_attempt to false and fill remaining fields with sensible defaults (or empty values).

Be precise. Do not hallucinate attributes the user did not mention.
"""

EXTRACTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_retrieval_attempt": {
            "type": "BOOLEAN",
            "description": "True if the text describes a specific attempt to find/retrieve a photo in Google Photos."
        },
        "source_platform": {
            "type": "STRING",
            "enum": ["reddit", "play_store", "app_store", "help_community", "youtube", "social"]
        },
        "source": {
            "type": "STRING",
            "enum": ["Reddit", "Play Store", "App Store", "YouTube Comment", "Google Support Community", "Twitter/X"],
            "description": "Canonical user-facing source platform name."
        },
        "url_id": {
            "type": "STRING",
            "description": "Original URL or unique identifier of the source item."
        },
        "raw_text": {
            "type": "STRING",
            "description": "The original user complaint verbatim."
        },
        "photo_type": {
            "type": "STRING",
            "enum": ["document", "screenshot", "old_vacation", "pet", "family_event", "selfie", "landmark", "food", "receipt", "other"],
            "description": "Category of media the user is looking for."
        },
        "remembered_attributes": {
            "type": "ARRAY",
            "items": { "type": "STRING" },
            "description": "What the user successfully recalled (visual features, event, people, approximate time)."
        },
        "forgotten_attributes": {
            "type": "ARRAY",
            "items": { "type": "STRING" },
            "description": "What the user explicitly lacked (exact date, location name, file type, album)."
        },
        "search_strategy": {
            "type": "STRING",
            "enum": ["keyword_search", "scrolling_timeline", "album_browsing", "people_face_search", "location_search", "date_filter", "combined_filters", "google_lens", "other"],
            "description": "How the user attempted the search with incomplete memory."
        },
        "failure_point": {
            "type": "STRING",
            "description": "Why the app failed them (zero results, irrelevant results, too many results, crashed, etc.)."
        },
        "workaround": {
            "type": "STRING",
            "description": "What the user did instead (manual scroll, gave up, used another app, asked someone)."
        },
        "emotional_signal": {
            "type": "STRING",
            "enum": ["frustrated", "angry", "disappointed", "sad", "resigned", "neutral"],
            "description": "Emotional intensity / stakes of the lost photo."
        }
    },
    "required": [
        "is_retrieval_attempt", "source_platform", "url_id", "raw_text",
        "photo_type", "remembered_attributes", "forgotten_attributes",
        "search_strategy", "failure_point", "workaround", "emotional_signal"
    ]
}
