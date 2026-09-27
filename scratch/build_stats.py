import urllib.request
import json
import os

def fetch(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    print("Fetching clusters...")
    clusters_data = fetch("http://localhost:8000/api/clusters")
    
    print("Fetching synthesis...")
    synthesis_data = fetch("http://localhost:8000/api/synthesis")
    
    print("Fetching coverage...")
    coverage_data = fetch("http://localhost:8000/api/coverage")

    # Hardcode funnel metrics explicitly as requested by user
    funnel = {
        "total_ingested": 12808,
        "evaluated_relevant": 2405,
        "out_of_scope": 1715,
        "in_scope": 690
    }

    stats = {
        "funnel": funnel,
        "clusters": clusters_data.get("clusters", []),
        "synthesis": synthesis_data.get("synthesis", []),
        "source_counts": coverage_data.get("source_counts", {})
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "stats.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    print(f"Successfully wrote {out_path}")

if __name__ == "__main__":
    main()
