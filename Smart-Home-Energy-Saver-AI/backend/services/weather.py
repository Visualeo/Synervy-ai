"""
backend/services/weather.py
-----------------------------
Weather service using Open-Meteo API.
Original weather fetch logic from Smart Home Energy Saver MAF (attribution preserved).
"""

import requests
from datetime import datetime, timedelta

WEATHER_CODES = {
    0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy Fog", 51: "Light Drizzle", 61: "Rain",
    71: "Snow", 80: "Rain Showers", 95: "Thunderstorm"
}


def get_tomorrow_weather(latitude: float = 18.6298, longitude: float = 73.7997,
                          timezone: str = "Asia/Kolkata") -> dict:
    """Fetches tomorrow's weather using Open-Meteo API."""
    try:
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
        condition = WEATHER_CODES.get(weather_code, "Unknown")
        return {
            "date": tomorrow,
            "temp_high": temp_max,
            "temp_low": temp_min,
            "condition": condition,
            "weather_code": weather_code,
            "source": "open-meteo"
        }
    except Exception as e:
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        return {
            "date": tomorrow,
            "temp_high": 28.0,
            "temp_low": 18.0,
            "condition": "Partly Cloudy",
            "weather_code": 2,
            "source": "simulated",
            "error": str(e)
        }
