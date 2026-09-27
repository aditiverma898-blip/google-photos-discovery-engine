import random
from collections import Counter

def compute_cluster_metrics(cluster_records: list[dict], total_records: int) -> dict:
    """
    Computes metrics for a single cluster of records.
    """
    cluster_size = len(cluster_records)
    if cluster_size == 0:
        return {}

    # Source diversity
    sources = [r.get("source_platform", "unknown") for r in cluster_records]
    source_counts = dict(Counter(sources))
    distinct_sources = len(source_counts)
    total_possible_sources = 6  # reddit, play_store, app_store, help_community, youtube, social

    # Emotional Weight
    emotion_scores = {
        "angry": 1.0,
        "frustrated": 0.8,
        "sad": 0.7,
        "disappointed": 0.5,
        "resigned": 0.4,
        "neutral": 0.1
    }
    
    total_emotion = 0
    gave_up_count = 0
    
    failure_points = []
    
    for r in cluster_records:
        emotion = r.get("emotional_signal", "neutral").lower()
        total_emotion += emotion_scores.get(emotion, 0.1)
        
        workaround = (r.get("workaround") or "").lower()
        if "gave up" in workaround or "give up" in workaround or "nothing" in workaround:
            gave_up_count += 1
            
        failure_point = r.get("failure_point")
        if failure_point:
            failure_points.append(failure_point)

    # Compute weights
    emotional_weight = total_emotion / cluster_size
    workaround_weight = gave_up_count / cluster_size
    frequency_weight = cluster_size / total_records if total_records > 0 else 0
    source_diversity_weight = distinct_sources / total_possible_sources

    # Final Severity Score
    severity_score = (
        0.40 * emotional_weight +
        0.30 * workaround_weight +
        0.20 * frequency_weight +
        0.10 * source_diversity_weight
    )
    
    # Top 5 Failure Points
    fp_counts = Counter(failure_points)
    top_failure_points = [fp for fp, count in fp_counts.most_common(5)]
    
    # Representative quotes (up to 10)
    quotes = [r.get("raw_text") for r in cluster_records if r.get("raw_text")]
    # To be deterministic but diverse, we sample if we have more than 10
    random.seed(42)
    representative_quotes = random.sample(quotes, min(10, len(quotes)))
    
    return {
        "record_count": cluster_size,
        "source_diversity": source_counts,
        "severity_score": min(1.0, max(0.0, severity_score)), # Clamp between 0 and 1
        "top_failure_points": top_failure_points,
        "representative_quotes": representative_quotes
    }
