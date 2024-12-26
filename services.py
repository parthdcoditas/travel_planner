# # services.py
# from langgraph.graph import StateGraph, START, END
# from pydantic import BaseModel, Field
# from typing import Literal,Dict
# import requests
# from datetime import datetime
# from langchain.prompts import PromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_groq import ChatGroq
# from dotenv import load_dotenv
# import os

# load_dotenv()

# GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
# SERP_API_KEY = os.getenv("SERP_API_KEY")
# OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
# llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model="mixtral-8x7b-32768")

# class WeatherState(BaseModel):
#     destination: str = Field(default="")
#     start_date: str = Field(default="")
#     end_date: str = Field(default="")
#     weather_data: Dict = Field(default_factory=dict)
#     location_data: Dict = Field(default_factory=dict)
#     response_content: str = Field(default="")
#     error: str = Field(default="")
#     total_trip_days: int = Field(default=0)

# class ItineraryState(BaseModel):
#     weather_data: WeatherState = Field(default_factory=WeatherState)
#     context: str = Field(default="")
#     itinerary_content: str = Field(default="")
#     user_query: str = Field(default="")
#     error: str = Field(default="")

# class ItineraryOutput(BaseModel):
#     Day: str = Field(description="Day number, e.g., 'Day 1'")
#     Morning: str = Field(description="Activity planned for the morning and description about that activity")
#     Afternoon: str = Field(description="Activity planned for the afternoon and description about that activity")
#     Evening: str = Field(description="Activity planned for the evening and description about that activity")

# parser = JsonOutputParser(pydantic_object=ItineraryOutput)

# def fetch_location_data(state: WeatherState) -> WeatherState:
#     try:
#         geoapify_url = f"https://api.geoapify.com/v1/geocode/search?text={state.destination}&lang=en&limit=1&type=city&format=json&apiKey={GEOAPIFY_API_KEY}"
#         geo_response = requests.get(geoapify_url).json()
        
#         if "results" not in geo_response or not geo_response["results"]:
#             state.error = "Unable to fetch location details."
#             return state
            
#         state.location_data = geo_response["results"][0]
#         return state
#     except Exception as e:
#         state.error = str(e)
#         return state

# def fetch_weather_data(state: WeatherState) -> WeatherState:
#     try:
#         start_date_obj = datetime.strptime(state.start_date, "%Y-%m-%d")
#         end_date_obj = datetime.strptime(state.end_date, "%Y-%m-%d")
#         state.total_trip_days = (end_date_obj - start_date_obj).days + 1

#         location = state.location_data
#         weather_url = f"{OPEN_METEO_API}?latitude={location['lat']}&longitude={location['lon']}&daily=uv_index_clear_sky_max,weather_code,temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum&start_date={state.start_date}&end_date={state.end_date}"
#         weather_response = requests.get(weather_url).json()

#         if "daily" not in weather_response:
#             state.error = "Unable to fetch weather data."
#             return state

#         state.weather_data = weather_response
#         return state
#     except Exception as e:
#         state.error = str(e)
#         return state

# def analyze_weather(state: WeatherState) -> WeatherState:
#     try:
#         daily_weather = state.weather_data["daily"]
#         weather_context = [
#             f"Date: {daily_weather['time'][i]}, Max Temp: {daily_weather['temperature_2m_max'][i]}C, Min Temp: {daily_weather['temperature_2m_min'][i]}C, UV Index: {daily_weather['uv_index_clear_sky_max'][i]}, Weather Code: {daily_weather['weather_code'][i]}, Rain: {daily_weather['rain_sum'][i]}mm"
#             for i in range(len(daily_weather["time"]))
#         ]
        
#         context = "\n".join(weather_context)
#         prompt = PromptTemplate(
#             template='''Given the following weather context: {context}
#             Analyze the weather conditions for the specified days at the given location.
#             Do not specify the any weather data in the response and do not add anything else.
#             Just provide a response in which specify the dates when weather is not ideal for travelling.
#             If the weather is good throughout, confirm that as well.'''
#         )
        
#         llm_chain = prompt | llm
#         response = llm_chain.invoke({"context": context})
#         state.response_content = response.content
#         return state
#     except Exception as e:
#         state.error = str(e)
#         return state

# def fetch_places(state: ItineraryState) -> ItineraryState:
#     try:
#         categories = {
#             "tourism.attraction": state.weather_data.total_trip_days * 2,
#             "entertainment": state.weather_data.total_trip_days / 2,
#             "entertainment.culture": state.weather_data.total_trip_days / 2,
#             "catering.restaurant": state.weather_data.total_trip_days,
#             "accommodation": 2,
#         }
        
#         fetched_data = {}
#         for category, limit in categories.items():
#             params = {
#                 "categories": category,
#                 "filter": f"place:{state.weather_data.location_data['place_id']}",
#                 "limit": limit,
#                 "apiKey": GEOAPIFY_API_KEY,
#             }
#             response = requests.get("https://api.geoapify.com/v2/places", params=params).json()
#             if "features" in response:
#                 fetched_data[category] = [
#                     feature["properties"]["name"]
#                     for feature in response["features"]
#                     if "name" in feature["properties"]
#                 ]
#         state.context = "\n".join(
#             f"{category}: {', '.join(names)}"
#             for category, names in fetched_data.items()
#         )
        
#         return state
#     except Exception as e:
#         state.error = str(e)
#         return state

# def generate_initial_itinerary(state: ItineraryState) -> ItineraryState:
#     try:
#         prompt = PromptTemplate(
#             template='''Using the following data: {context}, generate a day-wise travel itinerary for {total_trip_days} days. 
#             Ensure the output is structured as JSON and matches the following schema:
#             {format_instructions}''',
#             input_variables=["context", "total_trip_days"],
#         )
        
#         llm_chain = prompt | llm
#         response = llm_chain.invoke({
#             "context": state.context, 
#             "total_trip_days": state.weather_data.total_trip_days,
#             "format_instructions": parser.get_format_instructions()
#         })
#         state.itinerary_content = response.content
#         return state
#     except Exception as e:
#         state.error = str(e)
#         return state

# def update_existing_itinerary(state: ItineraryState) -> ItineraryState:
#     try:
#         if not state.user_query:
#             return state
            
#         prompt = PromptTemplate(
#             template='''Given the current itinerary: {itinerary} and context: {context},
#             update it based on the user query: "{user_query}".
#             Make only the changes requested by the user while preserving the rest of the itinerary.
#             Ensure that the itinerary includes all the travel days and matches schema exactly.
#             Strictly ensure the output is structured as list of dictionaries and matches the following schema exactly:
#             {format_instructions}
#             [
#                 {{
#                     "Day": "Day 1",
#                     "Morning": "Activities with their descriptions",
#                     "Afternoon": "Activities with their descriptions",
#                     "Evening": "Activities with their descriptions"
#                 }}
#             ]
#             ''',
#             input_variables=["itinerary", "context", "user_query", "format_instructions"]
#         )
#         llm_chain = prompt | llm
#         response = llm_chain.invoke({
#             "context":state.context,
#             "itinerary": state.itinerary_content,
#             "user_query": state.user_query,
#             "format_instructions": parser.get_format_instructions()
#         })
#         state.itinerary_content = response.content
#         return state
#     except Exception as e:
#         state.error = str(e)
#         return state

# def should_continue_weather(state: WeatherState) -> Literal["analyze_weather", END]:
#     if state.error:
#         return END
#     return "analyze_weather"

# def should_continue_itinerary(state: ItineraryState) -> Literal["generate_initial_itinerary", "update_existing_itinerary", END]:
#     if state.error:
#         return END
#     if state.user_query:
#         return "update_existing_itinerary"
#     return "generate_initial_itinerary"

# def create_weather_workflow() -> StateGraph:
#     workflow = StateGraph(WeatherState)
    
#     # Add nodes
#     workflow.add_node("fetch_location", fetch_location_data)
#     workflow.add_node("fetch_weather", fetch_weather_data)
#     workflow.add_node("analyze_weather", analyze_weather)
    
#     # Add edges
#     workflow.add_edge(START, "fetch_location")
#     workflow.add_edge("fetch_location", "fetch_weather")
#     workflow.add_conditional_edges(
#         "fetch_weather",
#         should_continue_weather
#     )
#     workflow.add_edge("analyze_weather", END)
    
#     return workflow.compile()

# def create_itinerary_workflow() -> StateGraph:
#     workflow = StateGraph(ItineraryState)
    
#     # Add nodes
#     workflow.add_node("fetch_places", fetch_places)
#     workflow.add_node("generate_initial_itinerary", generate_initial_itinerary)
#     workflow.add_node("update_existing_itinerary", update_existing_itinerary)
    
#     # Add edges
#     workflow.add_edge(START, "fetch_places")
#     workflow.add_conditional_edges(
#         "fetch_places",
#         should_continue_itinerary
#     )
#     workflow.add_edge("generate_initial_itinerary", END)
#     workflow.add_edge("update_existing_itinerary", END)
    
#     return workflow.compile()