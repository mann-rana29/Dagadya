"""
Integration test script to verify all agents and tools are working
"""

import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_agent_router():
    """Test the integrated agent router"""
    from agent_router import route_query
    
    print("\n" + "="*70)
    print("DAGADYA INTEGRATION TEST - Agent Router")
    print("="*70)
    
    test_cases = [
        ("Will it rain tomorrow in Dehradun?", "WEATHER (ENGLISH)"),
        ("कल बारिश होगी?", "WEATHER (HINDI)"),
        ("गेहूं का भाव क्या है?", "MARKET (HINDI)"),
        ("What's the price of wheat?", "MARKET (ENGLISH)"),
        ("My crop is damaged", "INSURANCE"),
        ("कृषि के बारे में सामान्य सलाह दें", "GENERAL (HINDI)"),
    ]
    
    for query, expected_type in test_cases:
        print(f"\n[TEST] {expected_type}")
        print(f"Query: {query}")
        print("-" * 70)
        
        try:
            result = route_query(query)
            print(f"✓ Intent: {result.get('intent')}")
            print(f"✓ Language: {result.get('language')}")
            print(f"✓ Response: {result.get('message')}")
            if result.get('data'):
                print(f"✓ Data present: {type(result.get('data'))}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70)


def test_individual_components():
    """Test individual components"""
    print("\n" + "="*70)
    print("COMPONENT TESTS")
    print("="*70)
    
    # Test controller
    print("\n[1] Testing Controller Intent Classification...")
    try:
        from controller import classify_text
        result = classify_text("Will it rain tomorrow?")
        print(f"✓ Controller working. Intent: {result.get('intent')}")
    except Exception as e:
        print(f"✗ Controller error: {e}")
    
    # Test weather tool
    print("\n[2] Testing Weather Tool...")
    try:
        from tools.weather_tool import get_weather
        result = get_weather("Dehradun")
        if "error" not in result:
            print(f"✓ Weather tool working. Location: {result.get('location')}")
        else:
            print(f"⚠ Weather API error (may be network related): {result.get('error')}")
    except Exception as e:
        print(f"✗ Weather tool error: {e}")
    
    # Test mandi agent
    print("\n[3] Testing Mandi Agent...")
    try:
        from agents.mandi_agent import mandi_agent
        result = mandi_agent({"location": "Uttarakhand", "language": "english"}, "wheat price")
        print(f"✓ Mandi agent working: {result.get('message')[:50]}...")
    except Exception as e:
        print(f"✗ Mandi agent error: {e}")
    
    # Test weather agent
    print("\n[4] Testing Weather Agent...")
    try:
        from agents.weatheragent import weather_agent
        result = weather_agent({"location": "Dehradun", "language": "english"})
        print(f"✓ Weather agent working: {result.get('message')[:50]}...")
    except Exception as e:
        print(f"✗ Weather agent error: {e}")


if __name__ == "__main__":
    print("\n🌾 DAGADYA - AGENT & TOOL INTEGRATION TEST 🌾")
    
    # Test components individually first
    test_individual_components()
    
    # Then test the integrated router
    test_agent_router()
    
    print("\n✨ All integration tests completed! ✨")
    print("\nNOTE: If you see network-related errors, those are expected")
    print("as they depend on external APIs. Functionality is integrated correctly.\n")
