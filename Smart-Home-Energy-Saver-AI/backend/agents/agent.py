"""
agent.py
----------
Enhanced agent architecture for Home Energy Saver using Microsoft Agent Framework (MAF).

Agents:
- UsageCollectorAgent: Collects last’s usage from CSV and tomorrow’s forecasts
- RecommendationAgent: Analyzes actual vs. forecasted usage and generates optimized suggestions
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import requests
from pydantic import BaseModel, Field
from agent_framework import ai_function
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

from prediction import predict_next_day_kwh


# -------------------------------
# Constants & Config
# -------------------------------
CSV_PATH = "./data/appliance_usage.csv"
CURRENCY = "INR"

# -------------------------------
# Helper Functions
# -------------------------------
def iso_date(dt: datetime) -> str:
    """Format datetime to ISO date string."""
    return dt.strftime("%Y-%m-%d")


def safe_json_extract(response_text: str) -> Dict[str, Any]:
    """Extract valid JSON from a response text."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(response_text[start:end + 1])
        raise ValueError(f"Could not extract JSON from response: {response_text}")

# -------------------------------
# Data Models
# -------------------------------
@dataclass
class HomeProfile:
    """Dataclass to represent a household's energy usage profile."""
    hh_size: int
    appliances_present: List[str]
    rate_peak: float = 12.0
    rate_offpeak: float = 7.5
    tariff_peak_start: str = "18:00"
    tariff_peak_end: str = "22:00"
    latitude: float = 18.6298
    longitude: float = 73.7997
    timezone: str = "Asia/Kolkata"
    # Optional city name; if provided, we'll attempt to resolve to lat/lon
    city: Optional[str] = None


def geocode_city(city: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Return a list of geocoding matches for the given city string using Nominatim.

    Each item in the returned list contains at least: display_name, lat, lon.

    This is a light-weight helper so callers that only have a city name can
    resolve latitude/longitude without adding a heavy dependency.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": max_results}
        headers = {"User-Agent": "HomeEnergySaver/1.0 (+https://example.com)"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data:
            results.append({
                "display_name": item.get("display_name", ""),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "type": item.get("type"),
                "class": item.get("class"),
            })
        return results
    except Exception:
        return []
    

@ai_function(
    name="get_last_usage_from_csv",
    description="Load appliance usage data for the most recent date in the CSV"
)
def get_last_usage_from_csv(csv_path: str = CSV_PATH) -> dict:
    """Returns a dict of last usage metrics for all appliances."""
    try:
        df = pd.read_csv(csv_path, parse_dates=["date"])
        latest_date = df["date"].max()

        # Filter rows for the latest date
        latest_records = df[df["date"] == latest_date]

        # Convert Timestamp to string and ensure all values are serializable
        latest_records = latest_records.copy()
        latest_records["date"] = latest_records["date"].dt.strftime("%Y-%m-%d")
        latest_records["start_time"] = latest_records["start_time"].astype(str)
        latest_records["end_time"] = latest_records["end_time"].astype(str)

        return {
            "date": latest_date.strftime("%Y-%m-%d"),
            "usage": latest_records.to_dict(orient="records")
        }
    except Exception as e:
        raise RuntimeError(f"Error reading CSV: {str(e)}")
    
@ai_function(
    name="get_tomorrow_weather",
    description="Gets tomorrow's weather (high, low, condition) using Open-Meteo API."
)
def get_tomorrow_weather(latitude: float, longitude: float, timezone: str) -> dict:
    """Returns tomorrow's temperature high, low, and weather condition using Open-Meteo."""
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "daily": "temperature_2m_max,temperature_2m_min,weathercode",
        "forecast_days": 2
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    temp_max = data["daily"]["temperature_2m_max"][1]
    temp_min = data["daily"]["temperature_2m_min"][1]
    weather_code = data["daily"]["weathercode"][1]
    code_map = {0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast", 61: "Rain", 95: "Thunderstorm"}
    condition = code_map.get(weather_code, "Unknown")
    return {"date": tomorrow, "temp_high": temp_max, "temp_low": temp_min, "condition": condition}


@ai_function(
    name="forecast_next_day_kwh",
    description="Predicts appliance-level kWh usage directly using ML model"
)
def forecast_next_day_kwh(
    appliance: str,
    date: str,
    avg_temp: float,
    hh_size: int,
    is_weekend: int
) -> dict:
    """Returns the predicted kWh usage for a given appliance on a specific date."""
    try:
        return predict_next_day_kwh(
            appliance=appliance,
            ds_next=date,
            avg_temp=avg_temp,
            hh_size=hh_size,
            is_weekend=is_weekend
        )
    except Exception as e:
        raise RuntimeError(f"Prediction error: {str(e)}")


# -------------------------------
# Create Agents
# -------------------------------
def create_usage_collector_agent():
    instructions = """
You are the UsageCollectorAgent.

1. Load last appliance usage from CSV.
2. Get tomorrow's weather forecast.
3. For each appliance, gather next day's kWh forecast.

Return JSON ONLY:
{
  "last_usage": ...,  "weather": ...,  "forecasts": [...list of forecasts...]
}
"""
    client = AzureOpenAIChatClient(credential=AzureCliCredential())
    return client.create_agent(
        instructions=instructions,
        tools=[get_last_usage_from_csv, get_tomorrow_weather, forecast_next_day_kwh]
    )


def create_recommendation_agent():
    instructions = """
You are the RecommendationAgent.

- Take last usage vs. tomorrow's forecast from UsageCollectorAgent.
- Suggest optimized settings for ALL appliances.
- Be very mindful while generating the recommendations, please try to adhere to the actual realtime conditions, check its its feasible or practical to use the recommendation in real life scenario
- Dont be blunt in generating the optimize plan, if there is not opportunity to save, please say it, no need to force fit the recommendations
- You are a wise and smart energy optimizer, you take into consideration the real and actual scenarios into consideration by checking the feasibility of implementing the recommendation
- Estimate savings where possible.
- Format response like this, just an example for you to understand the response structure:

{
  "summary": " Tomorrow will be hotter than average (34°C).",
  "actions": [
    {
      "appliance": "Air Conditioning",
      "recommendation": "Set to 25°C between 9PM–5PM",
      "estimated_kwh_saving": 0.5,
      "estimated_cost_saving": 4.5,
      "currency": "INR"
    },
    ...
  ]
}
"""
    client = AzureOpenAIChatClient(credential=AzureCliCredential())
    return client.create_agent(instructions=instructions)



# -------------------------------
# Agent Execution
# -------------------------------
async def run_agents(profile: HomeProfile) -> dict:
    # Initialize agents
    collector_agent = create_usage_collector_agent()
    recommender_agent = create_recommendation_agent()

    # Resolve city -> lat/lon on the backend if a city was provided
    try:
        if getattr(profile, "city", None):
            geores = geocode_city(profile.city)
            if geores:
                sel = geores[0]
                try:
                    profile.latitude = float(sel.get("lat", profile.latitude))
                    profile.longitude = float(sel.get("lon", profile.longitude))
                except Exception:
                    # leave defaults if conversion fails
                    pass
    except Exception:
        # ignore geocoding failures and continue with defaults
        pass

    # Prepare initial prompt
    tomorrow = datetime.now() + timedelta(days=1)
    raw_prompt = json.dumps({
        "csv_path": CSV_PATH,
        "profile": profile.__dict__,
        "tomorrow_iso": iso_date(tomorrow),
        "is_weekend": 1 if tomorrow.weekday() >= 5 else 0,
    })

    # Execute usage collector agent
    collector_result = await collector_agent.run(f"Collect required info: {raw_prompt}")
    collector_data = safe_json_extract(collector_result.text)
    print("collector_result: ", collector_data)

    # Feed raw collector output to recommendation agent
    rec_input = json.dumps(collector_data)
    recommender_result = await recommender_agent.run(f"Analyze and recommend: {rec_input}")
    return safe_json_extract(recommender_result.text)


def run_agent(profile: HomeProfile) -> dict:
    """Wrapper sync method to launch async agent runs."""
    return asyncio.run(run_agents(profile))

if __name__=='__main__':
    # result = geocode_city("Pune", 1)
    # result = result[0]
    # output = get_tomorrow_weather(result['lat'], result['lon'], 'Asia/Kolkata')
    # print(output)
    # result = get_last_usage_from_csv(CSV_PATH)
    # print(result)
    profile = HomeProfile(
        hh_size=4,
        appliances_present=["Air Conditioning", "Washing Machine", "Dishwasher", "Microwave", "Computer"]
    )
    output = run_agent(profile)
    print(json.dumps(output, indent=2))

