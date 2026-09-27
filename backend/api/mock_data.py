MOCK_CLUSTERS = [
    {
        "cluster_id": 1,
        "label": "Background Object Recall",
        "description": "Users remember a prominent background object but forget the primary subject.",
        "severity_score": 0.75,
        "size": 500,
        "top_failure_points": ["Background objects not indexed", "Primary subject overshadows background"],
        "representative_quotes": [
            {"quote": "I know she was holding a blue coffee mug but searching 'blue mug' gives me nothing.", "source": "Reddit - r/googlephotos"},
            {"quote": "Trying to find the picture with the yellow taxi in the background.", "source": "Google Support Community"}
        ]
    },
    {
        "cluster_id": 2,
        "label": "Relative Time and Space Search",
        "description": "Users search using relative time (e.g., 'after my birthday') or relative locations.",
        "severity_score": 0.82,
        "size": 450,
        "top_failure_points": ["Relative temporal parsing fails", "No support for event-based offsets"],
        "representative_quotes": [
            {"quote": "I want the photos taken a few days after my birthday in Paris.", "source": "App Store"},
            {"quote": "Searching for 'weekend before Halloween' doesn't work.", "source": "Twitter/X"}
        ]
    },
    {
        "cluster_id": 3,
        "label": "Aesthetic and Weather Context",
        "description": "Users search by the mood, weather, or aesthetic of the photo.",
        "severity_score": 0.65,
        "size": 300,
        "top_failure_points": ["Lack of weather metadata indexing", "Emotion and mood are not extracted"],
        "representative_quotes": [
            {"quote": "I'm looking for a rainy day at a cafe, but it just shows me pictures of coffee.", "source": "Reddit - r/googlephotos"},
            {"quote": "Why can't I search for 'gloomy weather' or 'sad mood'?", "source": "Google Support Community"}
        ]
    },
    {
        "cluster_id": 4,
        "label": "Abstract Concept and Meme Retrieval",
        "description": "Users look for memes, screenshots, or abstract ideas rather than physical objects.",
        "severity_score": 0.60,
        "size": 250,
        "top_failure_points": ["OCR text not prioritized for abstract concepts", "Semantic understanding of memes is lacking"],
        "representative_quotes": [
            {"quote": "Trying to find a screenshot of a funny meme about cats, but searching 'cat meme' just shows actual cats.", "source": "App Store"},
            {"quote": "I need the screenshot with the quote about persistence.", "source": "Reddit - r/googlephotos"}
        ]
    },
    {
        "cluster_id": 5,
        "label": "Action and Event-Based Recall",
        "description": "Users remember what was happening in the media (actions/events) but lack text keywords.",
        "severity_score": 0.85,
        "size": 650,
        "top_failure_points": ["Search indexes static nouns over dynamic verbs", "Action and event context not extracted"],
        "representative_quotes": [
            {"quote": "I'm looking for the video where my dog was barking at the TV, but 'barking dog' shows nothing.", "source": "Reddit - r/googlephotos"},
            {"quote": "Can't find that picture of me blowing out candles, 'birthday' just shows cakes without me.", "source": "Play Store"}
        ]
    }
]

MOCK_SYNTHESIS = [
    {
        "question_id": 1,
        "question_text": "What kinds of old photos do users struggle to retrieve?",
        "answer_text": "Users struggle to retrieve older photos when their search relies on contextual, environmental, or relative metadata rather than simple, high-level subject nouns. Specifically, users face high retrieval failure rates when looking for photos characterized by background details (Background Object Recall, ID 1, n=913), temporal or spatial offsets (Relative Time and Space Search, ID 2, n=202), and specific ambient conditions like mood, weather, or aesthetic (Aesthetic and Weather Context, ID 3, n=119). Because the indexing system heavily prioritizes primary subjects or static entities, historical photos embedded in complex backgrounds or associated with relative timeframes remain hidden.",
        "evidence": {
            "cited_clusters": [
                1,
                2,
                3
            ],
            "verbatim_quotes": [
                "I want pictures from yesterday and the day before and last year in 4 years ago I cannot find my photos is what I hate about this app!",
                "For example, if you search for December 2017, it won\u2019t show all photos from December 2017 (that would be too easy, right?), instead it\u2019s showing you a subset of those + some photos that were not even taken in December 2017."
            ]
        }
    },
    {
        "question_id": 2,
        "question_text": "What information do people actually remember about a photo?",
        "answer_text": "When attempting to retrieve lost or buried media, users consistently retain specific qualitative anchors regarding the memory. Based on the in-scope clusters, users remember prominent background objects or secondary scene context (ID 1), relative temporal markers or spatial relationships (ID 2), and atmospheric, emotional, or environmental properties such as lighting, weather, and aesthetic mood (ID 3). Furthermore, they often recall general chronological timeframes (e.g., 'after my birthday' or specific years) or specific relational events, even though they lack exact database keywords or precise EXIF timestamps.",
        "evidence": {
            "cited_clusters": [
                1,
                2,
                3
            ],
            "verbatim_quotes": [
                "For example, I want to show photos I took in Japan that don't have my face on them, then I search like this...",
                "I'm looking for two animated photos that show up in \"Photos\" under \"yesterday\", what effing folder are they in because when I go to \"Albums\" they are no where to be found!"
            ]
        }
    },
    {
        "question_id": 3,
        "question_text": "What information have they forgotten?",
        "answer_text": "Users frequently forget precise technical and structural metadata required by rigid search algorithms. Across the core failure clusters, users routinely forget exact calendar dates, specific file naming conventions, original filenames, and primary subjects in favor of background elements (ID 1). Additionally, they forget exact calendar offsets needed for relative temporal queries (ID 2) and precise atmospheric descriptors or explicit weather tags (ID 3). This disconnect between human autobiographical memory\u2014which is relational and contextual\u2014and database requirements causes search queries to return zero results or irrelevant noise.",
        "evidence": {
            "cited_clusters": [
                1,
                2,
                3
            ],
            "verbatim_quotes": [
                "Searching photos by day and date no longer working In my Google Photos library, I used to be able to search for all photos posted on a particular date, across all years.",
                "also the search for any of my Pic is difficult when I'm trying to find a specific one but any of the key words don't make it pop up so I end up just having to scroll."
            ]
        }
    },
    {
        "question_id": 4,
        "question_text": "How do users formulate searches when their memory is incomplete?",
        "answer_text": "When memory is incomplete, users employ associative and exploratory search strategies. They construct queries utilizing relative temporal and spatial offsets (e.g., searching relative to an event or general timeframe like 'after my birthday'), attempt multi-attribute filtering combining background objects with subject exclusions, or rely on broad categorical keywords. When these query formulations fail due to system limitations in parsing relative time, background entities, or mood, users are forced to abandon semantic search entirely and resort to manual, tedious timeline scrolling.",
        "evidence": {
            "cited_clusters": [
                1,
                2,
                3
            ],
            "verbatim_quotes": [
                "I'd like to access photos from years earlier, 2008 to be exact, and that will definitely take forever to load, and I'll have to keep scrolling until I get there.",
                "For example, I want to show photos I took in Japan that don't have my face on them, then I search like this: Japan +Hans -Julia"
            ]
        }
    },
    {
        "question_id": 5,
        "question_text": "Which in-scope cluster causes most frustration?",
        "answer_text": "Among the in-scope vague memory retrieval clusters, Background Object Recall (Cluster ID 1) causes the most verified user frustration, representing 913 complaints (significantly outscaling Relative Time and Space Search at 202 complaints and Aesthetic and Weather Context at 119 complaints). Users express severe frustration because while advanced vision models clearly recognize objects within an image, the search architecture aggressively prioritizes primary foreground subjects while failing to index prominent background elements. This forces users to engage in complex, undocumented query workarounds or revert to manual scanning of massive libraries.",
        "evidence": {
            "cited_clusters": [
                1,
                2,
                3
            ],
            "verbatim_quotes": [
                "I ask for \"yellow truck\" and it finds 2 out of the 10 different days I had taken pictures of yellow trucks. They're all banana yellow and the images contain a truck and nothing else.",
                "9 out of 10 of my searches results in \"No Results\" found. Only the most basic and broad searches work. If you search for \"Dog\", you will get some results, but if you search for \"Big Dog\", you will get No Results."
            ]
        }
    }
]

def mock_search_response(query: str):
    return {
        "query": query,
        "match_status": "Confident Match",
        "threshold": 0.45,
        "nearest_cluster": {
            "cluster_id": 1,
            "label": "Subject & Media Retrieval Difficulties",
            "description": f"User feedback related to searching for subjects like '{query}'.",
            "severity_score": 0.85,
            "distance": 0.2841
        },
        "similar_records": [
            {
                "id": 1,
                "cluster_id": 1,
                "source": "Play Store",
                "source_platform": "play_store",
                "raw_text": f"I tried searching for {query} but Google Photos returned completely unrelated photos or empty results.",
                "failure_point": "Subject recognition failed on vague query",
                "search_strategy": "Vague entity description",
                "distance": 0.2410,
                "is_confident": True
            },
            {
                "id": 2,
                "cluster_id": 1,
                "source": "Reddit",
                "source_platform": "reddit",
                "raw_text": f"Cannot find photos when searching for {query}.",
                "failure_point": "Multi-constraint entity indexing failure",
                "search_strategy": "Subject search",
                "distance": 0.3120,
                "is_confident": True
            }
        ]
    }
