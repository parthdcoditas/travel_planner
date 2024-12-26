import requests
from models import ItineraryState
from config import GEOAPIFY_API_KEY, llm, parser
from langchain.prompts import PromptTemplate

def fetch_places(state: ItineraryState) -> ItineraryState:
    try:
        categories = {
            "tourism.attraction": state.weather_data.total_trip_days * 2,
            "entertainment": state.weather_data.total_trip_days / 2,
            "entertainment.culture": state.weather_data.total_trip_days / 2,
            "catering.restaurant": state.weather_data.total_trip_days,
            "accommodation": 2,
        }
        
        fetched_data = {}
        for category, limit in categories.items():
            params = {
                "categories": category,
                "filter": f"place:{state.weather_data.location_data['place_id']}",
                "limit": limit,
                "apiKey": GEOAPIFY_API_KEY,
            }
            response = requests.get("https://api.geoapify.com/v2/places", params=params).json()
            if "features" in response:
                fetched_data[category] = [
                    feature["properties"]["name"]
                    for feature in response["features"]
                    if "name" in feature["properties"]
                ]
        state.context = "\n".join(
            f"{category}: {', '.join(names)}"
            for category, names in fetched_data.items()
        )
        
        return state
    except Exception as e:
        state.error = str(e)
        return state

def generate_initial_itinerary(state: ItineraryState) -> ItineraryState:
    try:
        prompt = PromptTemplate(
            template='''You are an Itinerary generating specialist.

            **Context**: {context}

            **INSTRUCTIONS**:
            - Generate a day-wise travel itinerary for {total_trip_days} days.
            - There are going to be many locations in the context, but you would have to take only the required locations in a day.
            - Keep 3 locations in a day in the itinerary.
            - On the first day, include accommodation, and every day must have a restaurant planned.
            - From each category, include only a few locations. It's not needed to have the entire category in the itinerary, and do not repeat places.
            - Your output should be directly JSON parsable, so do not add extra information.

            **STRICT NOTE**:
            - Match the schema of the input itinerary.
            - Do not add extra information like notes or explanations in the response.
            - Generate the itinerary for {total_trip_days} days, no more, no less.
            - Ensure the output is structured as JSON and matches the following schema:
                {format_instructions}
            ''',
            input_variables=["context", "total_trip_days", "format_instructions"]
        )

        
        llm_chain = prompt | llm
        response = llm_chain.invoke({
            "context": state.context, 
            "total_trip_days": state.weather_data.total_trip_days,
            "format_instructions": parser.get_format_instructions()
        })
        state.itinerary_content = response.content
        return state
    except Exception as e:
        state.error = str(e)
        return state

def update_existing_itinerary(state: ItineraryState) -> ItineraryState:
    try:
        if not state.user_query:
            return state
            
        prompt = PromptTemplate(
            template='''You are an Itinerary generating specialist.

            **Current itinerary**: {itinerary} 

            **Context**: {context}

            **User query**: "{user_query}"

            **INSTRUCTIONS**:- 
            - Make only the changes requested by the user while strictly preserving the rest of the itinerary.
            - There are going to be many locations in the context, but you would have to take only 3 locations in a day.
            - Do not put entire category in a Day and do not repeat places unless there are very few places.
            - Ensure that the itinerary includes all the travel days and matches schema exactly.
            
            **STRICT NOTE**
            - Match the schema of the input itinerary
            - Do not add any extra information like notes and headers in the response or message like this is the updated itinerary.
            - Generate response for {total_trip_days} days, do not generate for more or less days.
            - Update the required things and strictly keep the rest itinerary same.
            - Your output should be directly json parsable , so do not add extra information

            Strictly ensure the output is structured as list of dictionaries and matches the following schema exactly:
            {format_instructions}
            ''',
            input_variables=["itinerary", "context", "user_query", "format_instructions"]
        )
        llm_chain = prompt | llm
        response = llm_chain.invoke({
            "context":state.context,
            "itinerary": state.itinerary_content,
            "user_query": state.user_query,
            "total_trip_days": state.weather_data.total_trip_days,
            "format_instructions": parser.get_format_instructions()
        })
        print(parser.get_format_instructions())
        state.itinerary_content = response.content
        return state
    except Exception as e:
        state.error = str(e)
        return state