import os
import sys
import json
import asyncio
import logging
import numpy as np
import umap
import matplotlib.pyplot as plt

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_pool
from clustering.embedder import embed_records
from clustering.cluster_engine import perform_clustering
from clustering.metrics import compute_cluster_metrics
from clustering.labeler import generate_cluster_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_embedding_phase(pool):
    """Fetches records missing embeddings, embeds them, and updates the database."""
    # Use standard execute and cursor
    async with pool.execute("""
        SELECT id, failure_point, search_strategy 
        FROM feedback_records 
        WHERE embedding IS NULL
    """) as cursor:
        records = await cursor.fetchall()
        
    if not records:
        logger.info("No records need embedding.")
        return

    logger.info(f"Found {len(records)} records without embeddings.")
    records_list = [dict(r) for r in records]
    
    embedded_records = await embed_records(records_list)
    
    logger.info("Updating database with new embeddings...")
    
    # Store embedding as binary blob for sqlite-vec
    import struct
    
    update_query = "UPDATE feedback_records SET embedding = ? WHERE id = ?"
    update_data = []
    for r in embedded_records:
        if 'embedding' in r:
            vec = r['embedding']
            blob = struct.pack(f"{len(vec)}f", *vec)
            update_data.append((blob, r['id']))
    
    await pool.executemany(update_query, update_data)
    await pool.commit()
    logger.info("Embeddings saved to database.")

async def run_clustering_phase(pool):
    """Fetches all embeddings, clusters them, updates DB, computes metrics, and stores clusters."""
    import struct
    
    async with pool.execute("""
        SELECT id, source_platform, raw_text, photo_type, 
               remembered_attributes, forgotten_attributes, 
               search_strategy, failure_point, workaround, emotional_signal,
               embedding
        FROM feedback_records
        WHERE embedding IS NOT NULL
    """) as cursor:
        records = await cursor.fetchall()
        
    if not records:
        logger.info("No records with embeddings found for clustering.")
        return
        
    logger.info(f"Loaded {len(records)} records for clustering.")
    records_list = []
    embeddings = []
    for r in records:
        r_dict = dict(r)
        # Parse blob to float array
        blob = r_dict.pop('embedding')
        num_floats = len(blob) // 4
        emb_list = list(struct.unpack(f"{num_floats}f", blob))
        
        r_dict['embedding'] = emb_list
        embeddings.append(emb_list)
        records_list.append(r_dict)
        
    # 1. Perform Clustering
    labels, centroids = perform_clustering(embeddings)
    
    # 2. Assign cluster IDs to records and update DB
    update_cluster_query = "UPDATE feedback_records SET cluster_id = ? WHERE id = ?"
    update_cluster_data = []
    for record, label in zip(records_list, labels):
        record['cluster_id'] = int(label)
        update_cluster_data.append((int(label), record['id']))
        
    await pool.executemany(update_cluster_query, update_cluster_data)
    
    # 3. Process each cluster
    await pool.execute("DELETE FROM clusters")
    
    unique_labels = set(labels)
    total_records = len(records_list)
    
    for cluster_id in unique_labels:
        if cluster_id == -1:
            continue # Skip noise
            
        cluster_records = [r for r in records_list if r['cluster_id'] == cluster_id]
        logger.info(f"Processing cluster {cluster_id} with {len(cluster_records)} records...")
        
        metrics = compute_cluster_metrics(cluster_records, total_records)
        label_data = generate_cluster_label(metrics['representative_quotes'])
        
        # Save centroid as blob
        vec = centroids[cluster_id]
        centroid_blob = struct.pack(f"{len(vec)}f", *vec)
        
        insert_query = """
        INSERT INTO clusters (
            cluster_id, label, description, record_count, 
            source_diversity, severity_score, top_failure_points, 
            representative_quotes, centroid
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await pool.execute(
            insert_query,
            (
                int(cluster_id),
                label_data['label'],
                label_data['description'],
                metrics['record_count'],
                json.dumps(metrics['source_diversity']),
                metrics['severity_score'],
                json.dumps(metrics['top_failure_points']),
                json.dumps(metrics['representative_quotes']),
                centroid_blob
            )
        )
        
    await pool.commit()
    logger.info("Cluster metadata and metrics saved.")
    
    # 4. Generate 2D UMAP projection
    generate_umap_projection(embeddings, labels)

def generate_umap_projection(embeddings, labels):
    """Generates a 2D UMAP scatterplot and saves it to a PNG."""
    try:
        logger.info("Generating 2D UMAP projection for visualization...")
        # For small datasets, adjust parameters
        n_neighbors = min(15, len(embeddings) - 1) if len(embeddings) > 2 else 2
        reducer = umap.UMAP(n_neighbors=n_neighbors, n_components=2, metric='cosine', random_state=42)
        X_2d = reducer.fit_transform(np.array(embeddings))
        
        plt.figure(figsize=(10, 8))
        labels_arr = np.array(labels)
        
        # Plot noise first (gray)
        noise_idx = labels_arr == -1
        if np.any(noise_idx):
            plt.scatter(X_2d[noise_idx, 0], X_2d[noise_idx, 1], color='lightgray', s=10, alpha=0.5, label='Noise (-1)')
            
        # Plot clusters
        unique_clusters = set(labels) - {-1}
        cmap = plt.cm.get_cmap('tab20', len(unique_clusters))
        
        for i, cluster_id in enumerate(sorted(unique_clusters)):
            idx = labels_arr == cluster_id
            plt.scatter(X_2d[idx, 0], X_2d[idx, 1], color=cmap(i), s=20, label=f'Cluster {cluster_id}')
            
        plt.title("2D UMAP Projection of Retrieval Failure Clusters")
        # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        
        output_path = os.path.join(os.path.dirname(__file__), "..", "data", "clusters_2d_projection.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        plt.close()
        logger.info(f"Saved cluster visualization to {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate UMAP projection visualization: {e}")

async def run_pipeline():
    pool = await get_pool()
    try:
        logger.info("=== Starting Phase 3: Embedding Phase ===")
        await run_embedding_phase(pool)
        
        logger.info("=== Starting Phase 3: Clustering Phase ===")
        await run_clustering_phase(pool)
        
        logger.info("=== Phase 3 Completed Successfully ===")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(run_pipeline())
