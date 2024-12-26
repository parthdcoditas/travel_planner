import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from models import ItineraryOutput

load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
GEOAPIFY_API = "https://api.geoapify.com/v1/geocode/search"
llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model="llama3-70b-8192")
parser = JsonOutputParser(pydantic_object=ItineraryOutput)
