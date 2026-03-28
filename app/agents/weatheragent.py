from tools.weather_tool import get_weather
from groq import Groq
from dotenv import load_dotenv
import os
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


WEATHER_RULES = {
    "rain_warning_threshold": 10,
    "heavy_rain_threshold": 60
}

def analyze_weather(weather_data):
    rain_probs = weather_data["rain_probabilities"]
    max_rain = max(rain_probs)

    if max_rain > WEATHER_RULES["heavy_rain_threshold"]:
        return "heavy_rain"
    elif max_rain > WEATHER_RULES["rain_warning_threshold"]:
        return "light_rain"
    else:
        return "no_rain"


def weather_agent(intent_data):
    location = intent_data.get("location", "Dehradun")
    language = intent_data.get("language", "english").lower()

    weather = get_weather(location)

    if weather.get("error"):
        return {
            "message": "Location not found or weather unavailable.",
            "data": {}
        }

    logging.info(f"Weather Data: {weather}")

    condition = analyze_weather(weather)

    if language == "hindi":
        lang_instruction = "Respond ONLY in Hindi (Devanagari script). Do NOT use any English."
    else:
        lang_instruction = "Respond ONLY in English."

    prompt = f"""
You are an agricultural advisor.

Weather Condition: {condition}
Rain Probabilities: {weather['rain_probabilities']}
Temperature: {weather['temperature']}

Instructions:
- Give practical farming advice
- Keep it simple
- No technical jargon
- {lang_instruction}
"""
    MODELS = ["llama3-70b-8192", "mixtral-8x7b-32768"]

    advice = None

    for model in MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful agricultural advisor"},
                    {"role": "user", "content": prompt}
                ]
            )

            advice = response.choices[0].message.content
            break

        except Exception as e:
            logging.error(f"{model} failed: {e}")

    if not advice:
        if condition == "heavy_rain":
            advice = (
                "भारी बारिश की संभावना है। फसल को सुरक्षित रखें और जल निकासी सुनिश्चित करें।"
                if language == "hindi"
                else "Heavy rainfall expected. Protect crops and ensure proper drainage."
            )

        elif condition == "light_rain":
            advice = (
                "कुछ बारिश हो सकती है। सिंचाई की योजना उसी अनुसार बनाएं।"
                if language == "hindi"
                else "Some rain expected. Plan irrigation accordingly."
            )

        else:
            advice = (
                "मौसम अगले कुछ दिनों तक सामान्य रहने की संभावना है।"
                if language == "hindi"
                else "Weather looks stable for the next few days."
            )

    return {
        "message": advice,
        "data": weather
    }