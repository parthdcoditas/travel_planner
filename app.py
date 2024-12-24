from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from services import get_weather_analysis,generate_itinerary,update_itinerary, SERP_API_KEY
from markupsafe import Markup
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

weather_cache = {}
@app.post("/check-weather")
def check_weather(destination: str = Form(...), start_date: str = Form(...), end_date: str = Form(...)):
    global weather_cache
    result = get_weather_analysis(destination, start_date, end_date)

    if "error" in result:
        return {"error": result["error"]}

    # Save weather data for reuse in itinerary planning
    weather_cache["data"] = result["weather_data"]
    return {"content": result["content"]}


# @app.post("/plan-itinerary")
# def plan_itinerary():
#     global weather_cache
#     if "data" not in weather_cache:
#         return {"error": "Weather data not found. Please check the weather first."}

#     weather_data = weather_cache["data"]

#     try:
#         itinerary = generate_itinerary(weather_data)
#         return {"content": itinerary}
#     except Exception as e:
#         return {"error": str(e)}
    
@app.post("/update-itinerary")
def update_itinerary_route(user_query: str = Form(...)):
    global weather_cache
    if "data" not in weather_cache:
        return {"error": "Itinerary data not found. Please plan the trip first."}

    try:
        current_itinerary = generate_itinerary(weather_cache["data"])
        updated_itinerary = update_itinerary(current_itinerary, user_query)
        return {"content": Markup(updated_itinerary)}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/plan-trip-page", response_class=HTMLResponse)
def plan_trip_page(request: Request):
    global weather_cache
    if "data" not in weather_cache:
        return RedirectResponse("/")
    itinerary = generate_itinerary(weather_cache["data"])
    fetched_places = weather_cache["data"].dict().get("places", [])
    return templates.TemplateResponse(
        "itinerary_page.html",
        {"request": request, "itinerary": Markup(itinerary), "fetched_places": fetched_places}
    )

@app.post("/get-map-link")
def get_map_link(location_name: str = Form(...)):
    api_url = f"https://serpapi.com/search.json?engine=google_maps&q={location_name}&api_key={SERP_API_KEY}"
    response = requests.get(api_url).json()
    google_maps_url = response.get("search_metadata", {}).get("google_maps_url", "")
    if not google_maps_url:
        return {"error": "Unable to fetch Google Maps link"}
    return {"map_url": google_maps_url}
