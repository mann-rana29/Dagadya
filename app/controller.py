from groq import Groq
from dotenv import load_dotenv
import os
import logging
import json
import re

load_dotenv()
logging.basicConfig(level=logging.INFO)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("MODEL_NAME", "llama3-70b-8192")

def rule_based_classifier(text):
    original_text = text
    text = text.lower()

    if any(word in text for word in ["damage", "loss", "फसल खराब", "नुकसान"]):
        intent = "INSURANCE"
    elif any(word in text for word in ["mandi", "sell", "price", "बेचना", "भाव"]):
        intent = "MARKET"
    elif any(word in text for word in ["rain", "weather", "बारिश", "मौसम", "temperature", "heat", "cold"]):
        intent = "WEATHER"
    else:
        intent = "GENERAL"

    # Language detection
    if re.search(r'[\u0900-\u097F]', original_text):
        language = "hindi"
    else:
        language = "english"

    return {
        "intent": intent,
        "crop": None,
        "location": None,
        "language": language,
        "urgency": "LOW"
    }

def llm_classifier(query):
    prompt = f"""
You are an intent classification system.

Extract:
- intent (WEATHER, INSURANCE, MARKET, GENERAL)
- location (if mentioned, else null)
- language (hindi or english)

Return STRICT JSON only.

Examples:

Input: Will it rain tomorrow in Dehradun?
Output:
{{"intent":"WEATHER","location":"Dehradun","language":"english"}}

Input: कल बारिश होगी क्या?
Output:
{{"intent":"WEATHER","location":null,"language":"hindi"}}

Input: I want to sell crops in mandi
Output:
{{"intent":"MARKET","location":null,"language":"english"}}

Now classify:
Input: "{query}"
Output:
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )

    output = response.choices[0].message.content.strip()
    logging.info(f"LLM Output: {output}")

    # Clean JSON (important)
    json_start = output.find("{")
    json_end = output.rfind("}") + 1
    cleaned = output[json_start:json_end]

    return json.loads(cleaned)


# ---------------- MAIN CONTROLLER ----------------
def classify_text(query):
    try:
        result = llm_classifier(query)

        # Validate output (VERY IMPORTANT)
        if result.get("intent") not in ["WEATHER", "INSURANCE", "MARKET", "GENERAL"]:
            raise ValueError("Invalid intent from LLM")

        return {
            "intent": result.get("intent", "GENERAL"),
            "crop": None,
            "location": result.get("location"),
            "language": result.get("language", "english"),
            "urgency": "LOW"
        }

    except Exception as e:
        logging.error(f"LLM failed, using fallback: {e}")
        return rule_based_classifier(query)