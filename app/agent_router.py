"""
Agent Router - Routes user queries to appropriate agents based on intent classification
"""

import logging
from controller import classify_text
from agents.weatheragent import weather_agent
from agents.mandi_agent import mandi_agent
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def handle_general_query(query: str, language: str = "english") -> dict:
    """
    Handle general queries using LLM
    """
    if language.lower() == "hindi":
        lang_instruction = "Respond ONLY in Hindi (Devanagari script). Do NOT use any English."
    else:
        lang_instruction = "Respond ONLY in English."

    prompt = f"""
You are Dagadya, a helpful agricultural advisor for farmers.

User question: {query}

{lang_instruction}

Be concise (1-2 sentences max) and practical.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful agricultural advisor. Be concise and practical."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "message": response.choices[0].message.content,
            "intent": "GENERAL",
            "data": {}
        }
    except Exception as e:
        logging.error(f"Error handling general query: {e}")
        return {
            "message": "I'm here to help with weather, crop prices, and farming advice. How can I assist?",
            "intent": "GENERAL",
            "data": {}
        }


def route_query(query: str) -> dict:
    """
    Main router - classifies intent and routes to appropriate handler
    """
    logging.info(f"Routing query: {query}")
    
    # Step 1: Classify intent
    intent_data = classify_text(query)
    intent = intent_data.get("intent", "GENERAL")
    language = intent_data.get("language", "english")
    
    logging.info(f"Intent: {intent}, Language: {language}")
    
    # Step 2: Route to appropriate agent
    response = None
    
    if intent == "WEATHER":
        logging.info("Routing to Weather Agent")
        response = weather_agent(intent_data)
    
    elif intent == "MARKET":
        logging.info("Routing to Mandi Agent")
        response = mandi_agent(intent_data, query)
    
    elif intent == "INSURANCE":
        logging.info("Routing to Insurance Handler")
        response = handle_insurance_query(intent_data, query, language)
    
    else:
        logging.info("Routing to General Handler")
        response = handle_general_query(query, language)
    
    # Ensure response has required fields
    if "intent" not in response:
        response["intent"] = intent
    if "language" not in response:
        response["language"] = language
    
    return response


def handle_insurance_query(intent_data: dict, query: str, language: str) -> dict:
    """
    Handle insurance-related queries
    """
    if language == "hindi":
        lang_instruction = "Respond ONLY in Hindi (Devanagari script). Do NOT use any English."
    else:
        lang_instruction = "Respond ONLY in English."

    prompt = f"""
You are an agricultural insurance advisor helping farmers with PMFBY (Pradhan Mantri Fasal Bima Yojana) and other crop insurance schemes.

User question: {query}

Provide practical information about:
- Claim process
- Required documents
- Eligibility
- Benefits

{lang_instruction}

Keep it simple (1-2 sentences max).
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an agricultural insurance advisor. Be concise and helpful."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "message": response.choices[0].message.content,
            "data": {}
        }
    except Exception as e:
        logging.error(f"Error handling insurance query: {e}")
        default_msg = (
            "कृपया अपने स्थानीय कृषि कार्यालय या बीमा एजेंट से संपर्क करें।"
            if language == "hindi"
            else "Please contact your local agricultural office or insurance agent for more details."
        )
        return {
            "message": default_msg,
            "data": {}
        }


if __name__ == "__main__":
    # Test routing
    test_queries = [
        "Will it rain tomorrow in Dehradun?",
        "कल बारिश होगी?",
        "गेहूं का भाव क्या है?",
        "What's the price of wheat in mandi?",
        "My crop is damaged, how do I claim insurance?",
        "मुझे खेती के बारे में सामान्य सलाह दें"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        result = route_query(query)
        print(f"Intent: {result.get('intent')}")
        print(f"Message: {result.get('message')}")
