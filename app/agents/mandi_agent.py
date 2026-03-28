import re
from tools.weather_tool import get_weather
from agents.agmarknet_mandi import get_mandi_prices, format_mandi_for_gemini
from groq import Groq
from dotenv import load_dotenv
import os
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

COMMON_CROPS = ["wheat", "rice", "maize", "corn", "barley", "pulse", "chickpea", "lentil", 
                "soybean", "mustard", "potato", "onion", "tomato", "cotton", "sugarcane",
                "गेहूं", "चावल", "मक्का", "जौ", "दाल", "चना", "सोयाबीन", "सरसों", "आलू", 
                "प्याज", "टमाटर", "कपास", "गन्ना"]


def extract_crop_from_query(query: str):
    """
    Extract crop name from user query
    """
    query_lower = query.lower()
    
    for crop in COMMON_CROPS:
        if crop.lower() in query_lower:
            return crop
    
    return None


def mandi_agent(intent_data: dict, query: str) -> dict:
    """
    Market/Mandi agent - handles crop price queries
    """
    location = intent_data.get("location", "Uttarakhand")
    language = intent_data.get("language", "english").lower()
    
    # Extract crop from query
    crop = extract_crop_from_query(query)
    
    if not crop:
        return {
            "message": (
                "कृपया बताएं कि आप किस फसल का भाव जानना चाहते हैं? (जैसे: गेहूं, चावल, मक्का)"
                if language == "hindi"
                else "Please tell me which crop price you want to know. (e.g., wheat, rice, maize)"
            ),
            "data": {}
        }
    
    logging.info(f"Getting mandi prices for crop: {crop}")
    
    # Get mandi data
    mandi_data = get_mandi_prices(crop, state=location)
    
    if mandi_data.get("error"):
        return {
            "message": "Mandi data unavailable at the moment.",
            "data": {}
        }
    
    logging.info(f"Mandi Data: {mandi_data}")
    
    # Format data for LLM
    mandi_formatted = format_mandi_for_gemini(mandi_data)
    
    if language == "hindi":
        lang_instruction = "Respond ONLY in Hindi (Devanagari script). Do NOT use any English."
    else:
        lang_instruction = "Respond ONLY in English."
    
    prompt = f"""
You are an agricultural market advisor.

Current Mandi Data:
{mandi_formatted}

Based on this data, give practical advice to a farmer about selling their crop.

Instructions:
- Give actionable advice
- Keep it simple (1-2 sentences)
- No technical jargon
- {lang_instruction}
"""
    
    MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    advice = None
    
    for model in MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful agricultural market advisor"},
                    {"role": "user", "content": prompt}
                ]
            )
            advice = response.choices[0].message.content
            break
        except Exception as e:
            logging.error(f"{model} failed: {e}")
    
    if not advice:
        # Fallback response
        price_info = f"{mandi_data.get('mandi', 'local mandi')}: ₹{mandi_data.get('price', 'N/A')}"
        advice = (
            f"आपकी फसल का मौजूदा दाम {price_info} है।"
            if language == "hindi"
            else f"Current price at {price_info}."
        )
    
    return {
        "message": advice,
        "data": mandi_data
    }
