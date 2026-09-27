import json

with open('frontend/src/data/stats.json', 'r') as f:
    data = json.load(f)

print("Reconciliation Table:")
print(f"{'Cluster ID':<12} | {'Label':<40} | {'In-Scope':<10} | {'Excluded (Sync/Loss)':<20}")
print("-" * 90)

total_in_scope = 0
total_excluded = 0
for c in data['clusters']:
    print(f"{c['cluster_id']:<12} | {c['label']:<40} | {c['vague_memory_count']:<10} | {c['data_loss_count']:<20}")
    total_in_scope += c.get('vague_memory_count', 0)
    total_excluded += c.get('data_loss_count', 0)

print("-" * 90)
print(f"{'TOTAL':<12} | {'':<40} | {total_in_scope:<10} | {total_excluded:<20}")
