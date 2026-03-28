import requests


def get_mandi_prices(crop: str, state: str = "Uttarakhand") -> dict:
    """
    Fetch mandi price data from data.gov.in (Agmarknet)
    """

    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

    params = {
        "format": "json",
        "limit": 10,
        "filters[commodity]": crop.upper(),
        "filters[state]": state
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print("API Error:", response.status_code)
            return fallback_mandi_data(crop)

        data = response.json()
        records = data.get("records", [])

        if not records:
            return fallback_mandi_data(crop)

        best = records[0]

        return {
            "crop": crop,
            "mandi": best.get("market", "Unknown"),
            "district": best.get("district", "Unknown"),
            "price": best.get("modal_price", "N/A"),
            "min_price": best.get("min_price", "N/A"),
            "max_price": best.get("max_price", "N/A")
        }

    except Exception as e:
        print("Exception:", e)
        return fallback_mandi_data(crop)


def fallback_mandi_data(crop: str) -> dict:
    return {
        "crop": crop,
        "mandi": "Haridwar",
        "district": "Haridwar",
        "price": 2100,
        "min_price": 1900,
        "max_price": 2300
    }


def format_mandi_for_gemini(mandi: dict) -> str:
    return f"""
Fasal: {mandi['crop']}
Mandi: {mandi['mandi']} ({mandi['district']})
Daam: ₹{mandi['price']} / quintal
Range: ₹{mandi['min_price']} - ₹{mandi['max_price']}
"""

if __name__ == "__main__":
    crop = "wheat"

    print("Fetching mandi data...\n")

    mandi = get_mandi_prices(crop)

    print("Raw Data:", mandi)

    print("\nAdvice Format:\n")
    print(format_mandi_for_gemini(mandi))