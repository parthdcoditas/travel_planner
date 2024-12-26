import requests
from datetime import datetime
from models import WeatherState
from config import GEOAPIFY_API_KEY, OPEN_METEO_API, GEOAPIFY_API, llm
from langchain.prompts import PromptTemplate

def fetch_location_data(state: WeatherState) -> WeatherState:
    try:
        geoapify_url = f"{GEOAPIFY_API}?text={state.destination}&lang=en&limit=1&type=city&format=json&apiKey={GEOAPIFY_API_KEY}"
        geo_response = requests.get(geoapify_url).json()
        
        if "results" not in geo_response or not geo_response["results"]:
            state.error = "Unable to fetch location details."
            return state
            
        state.location_data = geo_response["results"][0]
        return state
    except Exception as e:
        state.error = str(e)
        return state

def fetch_weather_data(state: WeatherState) -> WeatherState:
    try:
        start_date_obj = datetime.strptime(state.start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(state.end_date, "%Y-%m-%d")
        state.total_trip_days = (end_date_obj - start_date_obj).days + 1

        location = state.location_data
        weather_url = f"{OPEN_METEO_API}?latitude={location['lat']}&longitude={location['lon']}&daily=uv_index_clear_sky_max,weather_code,temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum&start_date={state.start_date}&end_date={state.end_date}"
        weather_response = requests.get(weather_url).json()

        if "daily" not in weather_response:
            state.error = "Unable to fetch weather data."
            return state

        state.weather_data = weather_response
        return state
    except Exception as e:
        state.error = str(e)
        return state

def analyze_weather(state: WeatherState) -> WeatherState:
    try:
        daily_weather = state.weather_data["daily"]
        weather_context = [
            f"Date: {daily_weather['time'][i]}, Max Temp: {daily_weather['temperature_2m_max'][i]}C, Min Temp: {daily_weather['temperature_2m_min'][i]}C, UV Index: {daily_weather['uv_index_clear_sky_max'][i]}, Weather Code: {daily_weather['weather_code'][i]}, Rain: {daily_weather['rain_sum'][i]}mm"
            for i in range(len(daily_weather["time"]))
        ]
        
        context = "\n".join(weather_context)
        prompt = PromptTemplate(
            template='''You are a weather analyzer who would analyze the weather from the different parameters.

            **Weather Context**: {context}

            **INSTRUCTIONS**:
            - Analyze the weather conditions for the specified days at the given location.
            - Do not include any raw weather data such as weather codes or UV index in the response.
            - Specify the dates when the weather is not ideal for traveling and provide a brief reason (e.g., rain possible, snowfall likely, extreme heat).
            - If the weather is good throughout, confirm this as well.

            **STRICT NOTE**:
            - Do not provide additional information or explanations outside the scope of the analysis.
            - Ensure the output is concise and matches the requested analysis format.

            ''',
            input_variables=["context"]
        )

        llm_chain = prompt | llm
        response = llm_chain.invoke({"context": context})
        state.response_content = response.content
        return state
    except Exception as e:
        state.error = str(e)
        return state