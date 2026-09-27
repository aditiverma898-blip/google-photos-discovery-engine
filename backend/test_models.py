import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
        for model in data.get("models", []):
            if "flash" in model["name"]:
                print(model["name"], model.get("supportedGenerationMethods", []))
except Exception as e:
    print(e)
