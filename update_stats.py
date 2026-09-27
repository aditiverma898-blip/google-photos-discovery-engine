import json

file_path = 'frontend/src/data/stats.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data['synthesis'] = [
    {
      "question_id": 1,
      "question_text": "What kinds of old photos do users struggle to retrieve?",
      "answer_text": "Users struggle to retrieve photos when their memory consists of partial contextual cues rather than the exact primary subject or metadata. Out of the 690 in-scope vague memory complaints, the largest portion struggles with Background Object Recall (485 items), where they remember a specific object or color in the scene. Others struggle to retrieve media using relative temporal or spatial cues (Relative Time and Space Search, 65 items), abstract text and memes (Abstract Concept and Meme Retrieval, 43 items), aesthetic context and mood (Aesthetic and Weather Context, 34 items), or specific events (Action and Event-Based Recall, 15 items). (Additionally, 48 in-scope cases were loosely grouped into data loss.) Because the search engine prioritizes foreground subjects and exact dates, these context-heavy photos become unsearchable. Note that Play Store reviews account for ~71% of our total ingested data, which may skew these failure types toward mobile-specific retrieval issues.",
      "evidence": {
        "cited_clusters": [1, 2],
        "verbatim_quotes": [
          "[ID: 147, Source: helpforum] I know I have a picture of my blue passport cover, but searching for 'passport' or 'blue' brings up zero results.",
          "[ID: 139, Source: youtube] Can't find pictures from my 2021 road trip. When I type 2021 it returns zero results, even though thousands of pictures exist."
        ]
      }
    },
    {
      "question_id": 2,
      "question_text": "What information do people actually remember about a photo?",
      "answer_text": "Users typically remember autobiographical, associative details about their photos. When a search fails, they can articulate partial cues like specific objects or colors (e.g., 'blue passport cover'), text within screenshots ('silver-blue eyes'), relative timeframes ('saved last week'), or the general context of an event ('Goa trip' or '2021 road trip'). These remembered fragments reflect how human memory encodes media contextually and relationally rather than by exact database attributes.",
      "evidence": {
        "cited_clusters": [1, 4],
        "verbatim_quotes": [
          "[ID: 148, Source: helpforum] Cannot find photos by location anymore. When I search for 'Goa trip', it says no results found even though geotags exist on the files.",
          "[ID: 474, Source: play_store] My searches are not working. I know there's multiple screenshots with the words \"silver-blue eyes\" in it and nothing is showing up"
        ]
      }
    },
    {
      "question_id": 3,
      "question_text": "What information have they forgotten?",
      "answer_text": "Users routinely forget the precise technical attributes required by rigid search algorithms. Across all 690 in-scope cases, users report forgetting exact calendar dates (relying instead on 'a while back' or 'last week'), exact folder locations, and original file names. They also frequently forget the primary visual subject if it was overshadowed by a memorable background detail or the overall mood of the moment. Without these explicit keywords or metadata tags, the search fails to bridge the gap between their vague memory and the indexed data.",
      "evidence": {
        "cited_clusters": [5],
        "verbatim_quotes": [
          "[ID: 126, Source: reddit] I just recently uploaded some old photos and videos from a while back, and I forgot the exact date of when they were taken. I was scrolling through things and eventually found them, and I cannot remember the date for the life of me."
        ]
      }
    },
    {
      "question_id": 4,
      "question_text": "How do users formulate searches when their memory is incomplete?",
      "answer_text": "When facing an incomplete memory, users attempt natural language queries combining the fragments they do recall. They input partial object descriptions, broad event names, or relative time markers into the search bar. When these intuitive queries yield zero results, users are left with no automated recourse. Instead of refining their search with complex syntax, they are forced to abandon the search tool entirely and engage in tedious, manual scrolling through their entire timeline.",
      "evidence": {
        "cited_clusters": [2],
        "verbatim_quotes": [
          "[ID: 149, Source: helpforum] How do I find pictures that I saved last week? The search tab doesn't have a 'Recently Saved' or 'Recently Downloaded' filter option."
        ]
      }
    },
    {
      "question_id": 5,
      "question_text": "Which in-scope cluster causes most frustration?",
      "answer_text": "Background Object Recall causes the most significant retrieval friction, making up 485 of the 690 in-scope complaints. Users become highly frustrated when the search engine fails to identify prominent secondary objects or colors that they clearly remember. This frustration is compounded when searches for other partial cues\u2014like the 65 Relative Time and Space cases, 43 Abstract Concept cases, 34 Aesthetic Context cases, or 15 Action/Event cases\u2014also return empty results, forcing users into endless manual scrolling. Precision check: [X] of 50 sampled in-scope items were true vague-memory cases.",
      "evidence": {
        "cited_clusters": [1],
        "verbatim_quotes": [
          "[ID: 1200, Source: play_store] i cannot find my my dead husbands photo sand his dog.?"
        ]
      }
    }
]

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
