import sqlite3

def main():
    conn = sqlite3.connect('backend/data/discovery_engine.db')
    cursor = conn.cursor()

    action_keywords = ['video where', 'the moment when', 'action', 'event', 'running', 'jumping', 'dancing', 'playing', 'activity']
    abstract_keywords = ['screenshot', 'meme', 'funny picture', 'receipt', 'document', 'quote', 'infographic']

    action_conditions = ' OR '.join([f"raw_text LIKE '%{k}%'" for k in action_keywords])
    abstract_conditions = ' OR '.join([f"raw_text LIKE '%{k}%'" for k in abstract_keywords])

    # Count how many match the keywords but are currently NOT in cluster 4 or 5
    action_query = f'''
    SELECT count(*) FROM feedback_records 
    WHERE cluster_id != 5 AND ({action_conditions})
    '''

    abstract_query = f'''
    SELECT count(*) FROM feedback_records 
    WHERE cluster_id != 4 AND ({abstract_conditions})
    '''

    cursor.execute(action_query)
    action_count = cursor.fetchone()[0]

    cursor.execute(abstract_query)
    abstract_count = cursor.fetchone()[0]

    print(f'Total candidates for Action/Event (Cluster 5) in other clusters: {action_count}')
    print(f'Total candidates for Abstract/Meme (Cluster 4) in other clusters: {abstract_count}')

if __name__ == '__main__':
    main()
