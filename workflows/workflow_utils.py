from langgraph.graph import StateGraph, START, END
from models import WeatherState, ItineraryState
from service.weather_service import fetch_location_data, fetch_weather_data, analyze_weather
from service.itinerary_service import fetch_places, generate_initial_itinerary, update_existing_itinerary

def should_continue_weather(state: WeatherState):
    if state.error:
        return END
    return "analyze_weather"

def should_continue_itinerary(state: ItineraryState):
    if state.error:
        return END
    if state.user_query:
        return "update_existing_itinerary"
    return "generate_initial_itinerary"

def create_weather_workflow() -> StateGraph:
    workflow = StateGraph(WeatherState)

    workflow.add_node("fetch_location", fetch_location_data)
    workflow.add_node("fetch_weather", fetch_weather_data)
    workflow.add_node("analyze_weather", analyze_weather)

    workflow.add_edge(START, "fetch_location")
    workflow.add_edge("fetch_location", "fetch_weather")
    workflow.add_conditional_edges(
        "fetch_weather",
        should_continue_weather
    )
    workflow.add_edge("analyze_weather", END)
    
    return workflow.compile()

def create_itinerary_workflow() -> StateGraph:
    workflow = StateGraph(ItineraryState)

    workflow.add_node("fetch_places", fetch_places)
    workflow.add_node("generate_initial_itinerary", generate_initial_itinerary)
    workflow.add_node("update_existing_itinerary", update_existing_itinerary)

    workflow.add_edge(START, "fetch_places")
    workflow.add_conditional_edges(
        "fetch_places",
        should_continue_itinerary
    )
    workflow.add_edge("generate_initial_itinerary", END)
    workflow.add_edge("update_existing_itinerary", END)
    
    return workflow.compile()