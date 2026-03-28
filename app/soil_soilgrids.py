import requests


def get_soil_data(lat: float, lon: float) -> dict:
    """
    Fetch soil data from SoilGrids API
    No API key required
    """

    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    params = {
        "lat": lat,
        "lon": lon,
        "property": "phh2o,nitrogen,soc,clay,sand",
        "depth": "0-5cm",
        "value": "mean"
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print("API Error:", response.status_code)
            return fallback_soil_data()

        data = response.json()

        result = {}

        layers = data.get("properties", {}).get("layers", [])

        for layer in layers:
            name = layer.get("name")

            try:
                value = layer["depths"][0]["values"]["mean"]
            except:
                continue

            if name == "phh2o":
                result["pH"] = round(value / 10, 1)

            elif name == "nitrogen":
                result["nitrogen_mg_kg"] = round(value, 2)

            elif name == "soc":
                result["organic_carbon_g_kg"] = round(value, 2)

            elif name == "clay":
                result["clay_percent"] = round(value, 2)

            elif name == "sand":
                result["sand_percent"] = round(value, 2)

        if not result:
            return fallback_soil_data()

        return result

    except Exception as e:
        print("Exception:", e)
        return fallback_soil_data()


def fallback_soil_data():
    return {
        "pH": 6.5,
        "nitrogen_mg_kg": 50,
        "organic_carbon_g_kg": 6,
        "clay_percent": 30,
        "sand_percent": 40
    }

def format_soil_for_gemini(soil: dict, crop: str) -> str:
    """
    Convert soil data into simple Hindi advice
    """

    ph = soil.get("pH", 7)
    nitrogen = soil.get("nitrogen_mg_kg", 0)
    organic = soil.get("organic_carbon_g_kg", 0)

    advice = []

    # pH
    if ph < 5.5:
        advice.append("Mitti acidic hai — chuna daalen")
    elif ph > 8:
        advice.append("Mitti alkaline hai — gypsum daalen")
    else:
        advice.append("Mitti ka pH theek hai")

    # Nitrogen
    if nitrogen < 50:
        advice.append("Nitrogen kam hai — urea daalen")
    elif nitrogen < 100:
        advice.append("Nitrogen madhyam hai — thodi khad den")
    else:
        advice.append("Nitrogen achha hai")

    # Organic Carbon
    if organic < 5:
        advice.append("Organic carbon kam hai — compost daalen")
    else:
        advice.append("Mitti healthy hai")

    return f"Crop: {crop}\n" + " | ".join(advice)

if __name__ == "__main__":
    lat = 30.3165
    lon = 78.0322

    print("Fetching Soil Data...\n")

    soil = get_soil_data(lat, lon)

    print("Soil Data:")
    for k, v in soil.items():
        print(f"{k}: {v}")

    print("\nAdvice:\n")
    print(format_soil_for_gemini(soil, "wheat"))