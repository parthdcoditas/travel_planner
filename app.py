# app.py
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from workflows.workflow_utils import create_weather_workflow, create_itinerary_workflow
from models import WeatherState, ItineraryState
from config import SERP_API_KEY, parser
from markupsafe import Markup, escape
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

weather_cache = {}
weather_workflow = create_weather_workflow()
itinerary_workflow = create_itinerary_workflow()

@app.post("/check-weather")
def check_weather(destination: str = Form(...), start_date: str = Form(...), end_date: str = Form(...)):
    global weather_cache

    weather_state = WeatherState(
        destination=destination,
        start_date=start_date,
        end_date=end_date
    )

    result = weather_workflow.invoke(weather_state.dict())
    final_state = WeatherState(**result)
    
    if final_state.error:
        return {"error": final_state.error}

    weather_cache["data"] = final_state
    return {"content": final_state.response_content}

@app.get("/plan-trip-page", response_class=HTMLResponse)
def plan_trip_page(request: Request):
    global weather_cache
    if "data" not in weather_cache:
        return RedirectResponse("/")

    itinerary_state = ItineraryState(weather_data=weather_cache["data"])

    result = itinerary_workflow.invoke(itinerary_state.dict())
    final_state = ItineraryState(**result)
    print(final_state.itinerary_content)
    parsed_response = parser.parse(final_state.itinerary_content)
    itinerary_content = format_itinerary_html(parsed_response)
    if final_state.error:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": final_state.error}
        )
    
    return templates.TemplateResponse(
        "itinerary_page.html",
        {
            "request": request,
            "itinerary": Markup(itinerary_content),
            "fetched_places": final_state.context.split("\n")
        }
    )

@app.post("/update-itinerary")
def update_itinerary_route(user_query: str = Form(...)):
    global weather_cache
    if "data" not in weather_cache:
        return {"error": "Itinerary data not found. Please plan the trip first."}
    
    itinerary_state = ItineraryState(
        weather_data=weather_cache["data"],
        user_query=user_query
    )
    
    result = itinerary_workflow.invoke(itinerary_state.dict())
    final_state = ItineraryState(**result)

    if final_state.error:
        return {"error": final_state.error}

    try:
        print(final_state.itinerary_content)
        parsed_response = parser.parse(final_state.itinerary_content)
        formatted_content = format_itinerary_html(parsed_response)
        print(parsed_response)
    except Exception as e:
        return {"error": f"Failed to parse JSON response: {str(e)}"}
    
    return {"content": Markup(formatted_content)}

@app.post("/get-map-link")
def get_map_link(location_name: str = Form(...)):
    api_url = f"https://serpapi.com/search.json?engine=google_maps&q={location_name}&api_key={SERP_API_KEY}"
    response = requests.get(api_url).json()
    google_maps_url = response.get("search_metadata", {}).get("google_maps_url", "")
    if not google_maps_url:
        return {"error": "Unable to fetch Google Maps link"}
    return {"map_url": google_maps_url}

def format_itinerary_html(itinerary_json):
    html_content = ""
    for day in itinerary_json:
        html_content += f"<h2>{escape(day['Day'])}</h2>"
        html_content += f"<p><b>Morning:</b> {escape(day['Morning'])}</p>"
        html_content += f"<p><b>Afternoon:</b> {escape(day['Afternoon'])}</p>"
        html_content += f"<p><b>Evening:</b> {escape(day['Evening'])}</p>"
    return html_content