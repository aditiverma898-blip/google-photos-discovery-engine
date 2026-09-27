import sqlite3

def main():
    conn = sqlite3.connect('backend/data/discovery_engine.db')
    cursor = conn.cursor()

    action_keywords = ['video where', 'the moment when', 'action', 'event', 'running', 'jumping', 'dancing', 'playing', 'activity']
    abstract_keywords = ['screenshot', 'meme', 'funny picture', 'receipt', 'document', 'quote', 'infographic']

    action_conditions = ' OR '.join([f"raw_text LIKE '%{k}%'" for k in action_keywords])
    abstract_conditions = ' OR '.join([f"raw_text LIKE '%{k}%'" for k in abstract_keywords])

    # Assign abstract candidates
    update_abstract = f'''
    UPDATE feedback_records
    SET cluster_id = 4, is_retrieval_relevant = NULL, failure_category = NULL
    WHERE cluster_id != 4 AND ({abstract_conditions})
    '''
    cursor.execute(update_abstract)
    abstract_updated = cursor.rowcount

    # Assign action candidates (make sure we don't steal from cluster 4 we just updated)
    update_action = f'''
    UPDATE feedback_records
    SET cluster_id = 5, is_retrieval_relevant = NULL, failure_category = NULL
    WHERE cluster_id != 5 AND cluster_id != 4 AND ({action_conditions})
    '''
    cursor.execute(update_action)
    action_updated = cursor.rowcount

    conn.commit()

    print(f'Re-assigned {abstract_updated} records to Cluster 4 (Abstract/Meme).')
    print(f'Re-assigned {action_updated} records to Cluster 5 (Action/Event).')

if __name__ == '__main__':
    main()
