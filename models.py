from pydantic import BaseModel, Field
from typing import Dict

class WeatherState(BaseModel):
    destination: str = Field(default="")
    start_date: str = Field(default="")
    end_date: str = Field(default="")
    weather_data: Dict = Field(default_factory=dict)
    location_data: Dict = Field(default_factory=dict)
    response_content: str = Field(default="")
    error: str = Field(default="")
    total_trip_days: int = Field(default=0)
    
class ItineraryState(BaseModel):
    weather_data: WeatherState = Field(default_factory=WeatherState)
    context: str = Field(default="")
    itinerary_content: str = Field(default="")
    user_query: str = Field(default="")
    error: str = Field(default="")

class ItineraryOutput(BaseModel):
    Day: str = Field(description="Day number, e.g., 'Day 1'")
    Morning: str = Field(description="Activity planned for the morning and description about that activity")
    Afternoon: str = Field(description="Activity planned for the afternoon and description about that activity")
    Evening: str = Field(description="Activity planned for the evening and description about that activity")
