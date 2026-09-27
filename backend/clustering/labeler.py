import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Define schema for the label output
LABEL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "label": {
            "type": "STRING",
            "description": "A concise 3-5 word label for this group of Google Photos search failures."
        },
        "description": {
            "type": "STRING",
            "description": "A brief 1-2 sentence description summarizing the common failure pattern."
        }
    },
    "required": ["label", "description"]
}

SYSTEM_INSTRUCTION = "You are an expert product analyst categorizing user feedback."

def generate_cluster_label(quotes: list[str]) -> dict:
    """
    Calls Gemini to generate a label and description for a cluster based on its representative quotes.
    Returns a dict with 'label' and 'description'.
    """
    if not quotes:
        return {"label": "Unknown", "description": "No quotes available."}
        
    prompt = "Review the following user quotes describing Google Photos search failures:\n\n"
    for i, q in enumerate(quotes, 1):
        prompt += f"{i}. \"{q}\"\n"
        
    prompt += "\nGenerate a concise 3-5 word label and a brief description for this group."

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LABEL_SCHEMA,
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2
            )
        )
        
        result = json.loads(response.text)
        return result
    except Exception as e:
        logger.error(f"Error generating cluster label: {e}")
        return {"label": "Unlabeled Cluster", "description": "Failed to generate label."}
