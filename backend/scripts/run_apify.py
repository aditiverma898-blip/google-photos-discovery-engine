import os
import json
from pathlib import Path
from dotenv import load_dotenv
from apify_client import ApifyClient

# Safely point to the .env file in the backend directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get the token you saved in the .env file
apify_token = os.getenv("APIFY_TOKEN")
if not apify_token:
    raise ValueError("APIFY_TOKEN is missing. Please check your .env file.")

# Initialize the Apify Client
client = ApifyClient(apify_token)

print("Starting the Reddit Scraper...")

# Prepare the input for the Actor (Change the URL to the subreddit you want)
run_input = {
    "startUrls": [{"url": "https://www.reddit.com/r/technology/"}],
    "maxItems": 10, # Number of posts you want to scrape
    "sort": "new",
}

try:
    # Run the Reddit Scraper Lite Actor
    run = client.actor("trudax/reddit-scraper-lite").call(run_input=run_input)

    # Fetch the results from the Actor's dataset
    if hasattr(run, "default_dataset_id"):
        dataset_id = run.default_dataset_id
    elif hasattr(run, "get"):
        dataset_id = run.get("defaultDatasetId")
    else:
        dataset_id = run["defaultDatasetId"]
        
    items = client.dataset(dataset_id).list_items().items

    # Print the results
    print(f"Successfully scraped {len(items)} posts!\n")
    for item in items:
        print(f"Title: {item.get('title')}")
        print(f"Author: {item.get('author')}")
        print(f"URL: {item.get('url')}")
        print("-" * 40)

    # Save results to a file (in the backend/data directory)
    output_path = Path(__file__).parent.parent / "data" / "reddit_data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=4)
    print(f"Data saved to {output_path}")

except Exception as e:
    print(f"An error occurred with the Apify API: {e}")
