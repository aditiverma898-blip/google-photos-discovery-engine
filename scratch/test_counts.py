import sqlite3
import sys

def main():
    conn = sqlite3.connect('backend/data/discovery_engine.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.cluster_id, c.label,
               SUM(CASE WHEN f.is_retrieval_relevant = 1 THEN 1 ELSE 0 END) as verified_relevant,
               SUM(CASE WHEN f.is_retrieval_relevant = 1 AND f.failure_category = 'vague_memory_retrieval' THEN 1 ELSE 0 END) as in_scope,
               SUM(CASE WHEN f.is_retrieval_relevant = 1 AND f.failure_category = 'data_loss_sync' THEN 1 ELSE 0 END) as sync_loss,
               SUM(CASE WHEN f.is_retrieval_relevant = 1 AND f.failure_category = 'none_other' THEN 1 ELSE 0 END) as none_other,
               SUM(CASE WHEN f.is_retrieval_relevant = 1 AND f.failure_category IS NULL THEN 1 ELSE 0 END) as null_cat
        FROM clusters c
        LEFT JOIN feedback_records f ON c.cluster_id = f.cluster_id
        GROUP BY c.cluster_id
    """)

    rows = cursor.fetchall()
    all_passed = True

    print(f"{'Cluster':<35} | {'Relevant':<10} | {'Sum(Cats)':<10} | {'Pass?':<5}")
    print("-" * 70)

    for row in rows:
        cid, label, relevant, in_scope, sync_loss, none_other, null_cat = row
        relevant = relevant or 0
        in_scope = in_scope or 0
        sync_loss = sync_loss or 0
        none_other = none_other or 0
        null_cat = null_cat or 0

        sum_cats = in_scope + sync_loss + none_other
        passed = (relevant == sum_cats) and (null_cat == 0)

        status = "PASS" if passed else "FAIL"
        print(f"{label[:35]:<35} | {relevant:<10} | {sum_cats:<10} | {status:<5}")

        if not passed:
            all_passed = False
            print(f"  -> Discrepancy details: relevant={relevant}, in_scope={in_scope}, sync_loss={sync_loss}, none_other={none_other}, null_cat={null_cat}")

    conn.close()

    if all_passed:
        print("\nSUCCESS: All counts reconcile perfectly!")
        sys.exit(0)
    else:
        print("\nERROR: Counts do not reconcile.")
        sys.exit(1)

if __name__ == '__main__':
    main()
