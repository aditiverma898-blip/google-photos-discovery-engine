import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_and_filter_records(raw_responses: list[dict]) -> list[dict]:
    """
    Parses each Gemini response. Validates against schema (type checks, enum membership).
    Discards records where is_retrieval_attempt == false.
    Returns a list of valid records ready for database insertion.
    """
    valid_records = []
    total_records = len(raw_responses)
    discarded_non_retrieval = 0
    discarded_invalid = 0
    
    for item in raw_responses:
        try:
            # Assuming 'item' is a dict containing the parsed JSON from Gemini Structured Output
            if not item.get("is_retrieval_attempt", False):
                discarded_non_retrieval += 1
                continue
                
            # Perform basic validation
            required_keys = [
                "source_platform", "url_id", "raw_text", "photo_type",
                "remembered_attributes", "forgotten_attributes",
                "search_strategy", "failure_point", "emotional_signal"
            ]
            
            is_valid = True
            for key in required_keys:
                if key not in item or item[key] is None:
                    is_valid = False
                    break
                    
            if not is_valid:
                discarded_invalid += 1
                continue
                
            # Canonicalize or backfill source field
            raw_src = item.get("source") or item.get("source_platform")
            canon_map = {
                "play_store": "Play Store",
                "reddit": "Reddit",
                "youtube": "YouTube Comment",
                "youtube_comment": "YouTube Comment",
                "help_community": "Google Support Community",
                "helpforum": "Google Support Community",
                "app_store": "App Store",
                "appstore": "App Store",
                "social": "Twitter/X",
                "twitter": "Twitter/X"
            }
            canon_src = canon_map.get(str(raw_src).lower().strip()) if raw_src else None
            if not canon_src:
                logger.warning(f"Extracted record url_id='{item.get('url_id')}' has missing source platform: '{raw_src}'. Flagged for backfill.")
            item["source"] = canon_src

            # Keep the workaround field if it exists, otherwise set to None
            item["workaround"] = item.get("workaround", None)
            
            valid_records.append(item)
            
        except Exception as e:
            logger.error(f"Error validating record: {e}")
            discarded_invalid += 1

    discard_rate = ((discarded_non_retrieval + discarded_invalid) / total_records) * 100 if total_records > 0 else 0
    
    logger.info(f"Total processed: {total_records}")
    logger.info(f"Discarded (not retrieval attempt): {discarded_non_retrieval}")
    logger.info(f"Discarded (invalid schema): {discarded_invalid}")
    logger.info(f"Valid records: {len(valid_records)}")
    logger.info(f"Discard rate: {discard_rate:.2f}%")
    
    return valid_records
