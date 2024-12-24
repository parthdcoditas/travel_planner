import requests
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model="mixtral-8x7b-32768")
class WeatherData(BaseModel):
    lat: float
    lon: float
    place_id: str
    response_content: str
    total_trip_days: int

def get_weather_analysis(destination: str, start_date: str, end_date: str):
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_trip_days = (end_date_obj - start_date_obj).days + 1  

        # Fetch location data using Geoapify
        geoapify_url = f"https://api.geoapify.com/v1/geocode/search?text={destination}&lang=en&limit=1&type=city&format=json&apiKey={GEOAPIFY_API_KEY}"
        geo_response = requests.get(geoapify_url).json()

        if "results" not in geo_response or not geo_response["results"]:
            return {"error": "Unable to fetch location details."}

        location = geo_response["results"][0]
        lat, lon, place_id = location["lat"], location["lon"], location["place_id"]

        # Fetch weather data using Open Meteo
        weather_url = f"{OPEN_METEO_API}?latitude={lat}&longitude={lon}&daily=uv_index_clear_sky_max,weather_code,temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum&start_date={start_date}&end_date={end_date}"
        weather_response = requests.get(weather_url).json()

        if "daily" not in weather_response:
            return {"error": "Unable to fetch weather data."}

        daily_weather = weather_response["daily"]
        weather_context = [
            f"Date: {daily_weather['time'][i]}, Max Temp: {daily_weather['temperature_2m_max'][i]}C, Min Temp: {daily_weather['temperature_2m_min'][i]}C, UV Index: {daily_weather['uv_index_clear_sky_max'][i]}, Weather Code: {daily_weather['weather_code'][i]}, Rain: {daily_weather['rain_sum'][i]}mm"
            for i in range(len(daily_weather["time"]))
        ]

        context = "\n".join(weather_context)

        prompt = PromptTemplate(
            template='''Given the following weather context: {context}
            Analyze the weather conditions for the specified days at the given location.
            Do not specify the any weather data in the response and do not add anything else.
            Just provide a response in which specify the dates when weather is not ideal for travelling.
            If the weather is good throughout, confirm that as well.'''
        )

        llm_chain = prompt | llm
        response = llm_chain.invoke({"context": context})

        weather_data = WeatherData(
            lat=lat,
            lon=lon,
            place_id=place_id,
            response_content=response.content,
            total_trip_days=total_trip_days
        )

        return {"content": response.content, "weather_data": weather_data}

    except Exception as e:
        return {"error": str(e)}

def generate_itinerary(weather_data: WeatherData):
    categories = {
        "tourism.attraction": weather_data.total_trip_days * 2,
        "entertainment": weather_data.total_trip_days / 2,
        "entertainment.culture":weather_data.total_trip_days / 2,
        "catering.restaurant":weather_data.total_trip_days,
        "accommodation": 2,
    }
    api_url = "https://api.geoapify.com/v2/places"
    fetched_data = {}

    for category, limit in categories.items():
        params = {
            "categories": category,
            "filter": f"place:{weather_data.place_id}",
            "limit": limit,
            "apiKey": GEOAPIFY_API_KEY,
        }
        response = requests.get(api_url, params=params).json()
        if "features" in response:
            fetched_data[category] = [
                feature["properties"]["name"]
                for feature in response["features"]
                if "name" in feature["properties"]
            ]

    # Combine fetched data into a context for LLM
    context = "\n".join(
        f"{category}: {', '.join(names)}"
        for category, names in fetched_data.items()
    )
    itinerary_prompt = PromptTemplate(
        template='''Using the following data: {context}, generate a day-wise travel itinerary in the following format for the {total_trip_days}:
        There would be multiple locations present in the context, only use the required number of places for itinerary like
        in a day, 3 places could be visited at morning, afternoon and evening.
        Give the output in html format, Day in h2 tag, and other in p tag.
        Ensure the itinerary is logical, balanced, enjoyable, and takes into account any weather constraints.
        Ensure that for a day morning, afternoon and evening are strictly included.
        Format - 
        Day 1:-
        Morning - Location or activity name and description about that location
        Afternoon - Location or activity name and description about that location
        Evening - Location or activity name and description about that location
        ''',
        input_variables=["context", "total_trip_days"]
    )
    llm_chain = itinerary_prompt | llm 
    response = llm_chain.invoke({"context": context, "total_trip_days": weather_data.total_trip_days})

    return response.content 

def update_itinerary(itinerary: str, user_query: str) -> str:

    try:
        # Define a prompt to guide the LLM
        prompt = PromptTemplate(
            template='''The current travel itinerary is as follows:
            {itinerary}

            The user has requested the following changes: "{user_query}".
            Only make the changes given by user, keep the rest itinerary the same
            Make the changes logically and ensure it remains balanced and enjoyable.''',
            input_variables=["itinerary", "user_query"]
        )

        llm_chain = prompt | llm
        response = llm_chain.invoke({"itinerary": itinerary, "user_query": user_query})

        return response.content
    except Exception as e:
        return f"An error occurred while updating the itinerary: {str(e)}"
