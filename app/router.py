def route(intent):
    intent = intent["intent"].upper()

    if intent == "WEATHER":
        return "weather_agent"
    elif intent == "INSURANCE":
        return "insurance_agent"
    elif intent == "MARKET":
        return "market_agent"
    elif intent == "CROP_ADVISORY":
        return "crop_advisory_agent"
    else:
        return "general_agent"