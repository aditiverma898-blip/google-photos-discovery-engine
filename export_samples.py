import sqlite3
import pandas as pd
import numpy as np

# Connect to database
db_path = 'backend/data/discovery_engine.db'
conn = sqlite3.connect(db_path)

# Query in-scope data (690 items)
in_scope_query = """
SELECT id, source_platform as source, cluster_id as cluster, raw_text as full_text
FROM feedback_records
WHERE is_retrieval_relevant = 1 AND failure_category = 'vague_memory_retrieval'
"""
df_in_scope = pd.read_sql_query(in_scope_query, conn)

# Query excluded data (1715 items)
excluded_query = """
SELECT id, source_platform as source, cluster_id as cluster, raw_text as full_text
FROM feedback_records
WHERE is_retrieval_relevant = 1 AND failure_category = 'data_loss_sync'
"""
df_excluded = pd.read_sql_query(excluded_query, conn)

conn.close()

# A) precision_sample.csv: 50 random items
# 25 from Background Object Recall (cluster 1)
# 10 from Relative Time and Space (cluster 2)
# 15 from the rest (proportional)

cluster_1_sample = df_in_scope[df_in_scope['cluster'] == 1].sample(n=25, random_state=42)
cluster_2_sample = df_in_scope[df_in_scope['cluster'] == 2].sample(n=10, random_state=42)

# For proportional sampling of the rest, simple random sampling across the remaining rows achieves this naturally
rest_sample = df_in_scope[~df_in_scope['cluster'].isin([1, 2])].sample(n=15, random_state=42)

precision_df = pd.concat([cluster_1_sample, cluster_2_sample, rest_sample]).sample(frac=1, random_state=42).reset_index(drop=True)

# Add blank columns
precision_df['my_label_1_vague_memory'] = ''
precision_df['my_label_2_general_search_quality'] = ''
precision_df['my_label_3_data_loss'] = ''
precision_df['notes'] = ''

# Ensure correct column order
precision_cols = ['id', 'source', 'cluster', 'full_text', 'my_label_1_vague_memory', 'my_label_2_general_search_quality', 'my_label_3_data_loss', 'notes']
precision_df = precision_df[precision_cols]

precision_df.to_csv('precision_sample.csv', index=False)

# B) excluded_sample.csv: 40 random items from the 1,715 excluded
excluded_sample = df_excluded.sample(n=40, random_state=42).reset_index(drop=True)

# Add blank columns
excluded_sample['my_label_photo_gone'] = ''
excluded_sample['my_label_cant_find'] = ''
excluded_sample['notes'] = ''

# Ensure correct column order
excluded_cols = ['id', 'source', 'cluster', 'full_text', 'my_label_photo_gone', 'my_label_cant_find', 'notes']
excluded_sample = excluded_sample[excluded_cols]

excluded_sample.to_csv('excluded_sample.csv', index=False)

# Print row counts per cluster for both files
print("precision_sample.csv - Row counts per cluster:")
print(precision_df['cluster'].value_counts().sort_index().to_string())

print("\nexcluded_sample.csv - Row counts per cluster:")
print(excluded_sample['cluster'].value_counts().sort_index().to_string())
