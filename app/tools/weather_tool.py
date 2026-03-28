import requests

def get_weather(location):
    try:
        # Geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}"
        geo_res = requests.get(geo_url)
        geo_data = geo_res.json()

        if "results" not in geo_data or len(geo_data["results"]) == 0:
            return {"error": "Location not found"}

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # Weather API
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_probability_max,temperature_2m_max&timezone=auto"
        weather_res = requests.get(weather_url)
        weather_data = weather_res.json()

        daily = weather_data.get("daily", {})
        rain = daily.get("precipitation_probability_max", [])
        temp = daily.get("temperature_2m_max", [])

        if not rain or not temp:
            return {"error": "Weather data unavailable"}

        return {
            "location": location,
            "rain_probabilities": rain[:5],
            "temperature": temp[:5]
        }

    except Exception as e:
        return {"error": str(e)}