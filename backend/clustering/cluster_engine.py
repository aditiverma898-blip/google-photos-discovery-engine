import logging
import numpy as np
import umap
import hdbscan
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)

def perform_clustering(embeddings: list[list[float]]) -> tuple[list[int], dict[int, list[float]]]:
    """
    Performs clustering on a list of embeddings.
    1. Reduces dimensionality using UMAP (n_components=50).
    2. Clusters using HDBSCAN.
    3. Falls back to KMeans if HDBSCAN finds < 5 clusters.
    
    Returns:
        cluster_labels: List of cluster assignments (int) for each embedding (noise is -1).
        centroids: Dictionary mapping cluster_id to its centroid vector (768-d).
    """
    if not embeddings:
        return [], {}
        
    X = np.array(embeddings)
    
    logger.info(f"Reducing dimensionality of {len(embeddings)} vectors with UMAP...")
    # If we have very few samples (e.g. during testing), UMAP n_neighbors must be adjusted
    n_neighbors = min(15, len(embeddings) - 1) if len(embeddings) > 2 else 2
    n_components = min(50, len(embeddings) - 1) if len(embeddings) > 2 else 2
    
    if len(embeddings) > 50:
        reducer = umap.UMAP(n_neighbors=n_neighbors, n_components=n_components, metric='cosine', random_state=42)
        X_reduced = reducer.fit_transform(X)
    else:
        # Skip UMAP or use minimal reduction if dataset is extremely small (for testing)
        X_reduced = X

    logger.info("Clustering with HDBSCAN...")
    # Adjust min_cluster_size for very small datasets (e.g. testing)
    min_cluster_size = min(30, max(2, len(embeddings) // 5))
    min_samples = min(10, max(1, min_cluster_size // 3))
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean'
    )
    labels = clusterer.fit_predict(X_reduced)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    
    if n_clusters < 5 and len(embeddings) >= 8:
        logger.warning(f"HDBSCAN only found {n_clusters} clusters. Falling back to KMeans...")
        
        best_k = min(4, len(embeddings) - 1)
        best_score = -1
        max_k = min(10, len(embeddings) - 1)
        
        for k in range(min(4, len(embeddings) - 1), max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            k_labels = kmeans.fit_predict(X_reduced)
            score = silhouette_score(X_reduced, k_labels) if len(set(k_labels)) > 1 else -1
            
            if score > best_score:
                best_score = score
                best_k = k
                
        logger.info(f"Best KMeans silhouette score: {best_score:.4f} at k={best_k}")
        final_kmeans = KMeans(n_clusters=best_k, random_state=42, n_init='auto')
        labels = final_kmeans.fit_predict(X_reduced)
    else:
        logger.info(f"HDBSCAN found {n_clusters} valid clusters.")
        
    # Compute centroids for each valid cluster
    centroids = {}
    unique_labels = set(labels)
    for cluster_id in unique_labels:
        if cluster_id != -1:
            # Calculate centroid using original 768-d embeddings
            cluster_vectors = X[labels == cluster_id]
            centroid = np.mean(cluster_vectors, axis=0)
            centroids[cluster_id] = centroid.tolist()
            
    return labels.tolist(), centroids
