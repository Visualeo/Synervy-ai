"""
backend/agents/prediction.py
-----------------------------
Synervy AI – Prediction Agent
Forecasts appliance-level energy usage using ML models.
Wraps Prophet-based prediction from Smart Home Energy Saver (attribution preserved).
"""

from datetime import datetime, timedelta
from backend.services.weather import get_tomorrow_weather
from ml.prediction import predict_next_day_kwh
from backend.services.energy_data import get_appliance_list


class PredictionAgent:
    NAME = "PredictionAgent"

    def handle(self, message: str, context: dict) -> dict:
        """Generate ML-based energy forecasts for tomorrow."""
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        is_weekend = 1 if (datetime.now() + timedelta(days=1)).weekday() >= 5 else 0
        hh_size = context.get("hh_size", 4)

        weather = get_tomorrow_weather(
            context.get("latitude", 18.6298),
            context.get("longitude", 73.7997),
            context.get("timezone", "Asia/Kolkata")
        )
        avg_temp = (weather.get("temp_high", 25) + weather.get("temp_low", 18)) / 2
        appliances = get_appliance_list()

        forecasts = []
        total_predicted = 0.0
        for app in appliances:
            try:
                f = predict_next_day_kwh(app, tomorrow, avg_temp, hh_size, is_weekend)
                forecasts.append(f)
                total_predicted += f.get("predicted_kwh", 0)
            except Exception as e:
                forecasts.append({
                    "appliance": app,
                    "date": tomorrow,
                    "predicted_kwh": 1.5,
                    "error": str(e),
                    "simulated": True
                })
                total_predicted += 1.5

        # Assess risk from forecast
        risk = "LOW"
        if total_predicted > 18:
            risk = "CRITICAL"
        elif total_predicted > 13:
            risk = "HIGH"
        elif total_predicted > 8:
            risk = "MEDIUM"

        weather_note = (
            f"Tomorrow: {weather.get('temp_high', '?')}°C high / "
            f"{weather.get('temp_low', '?')}°C low, {weather.get('condition', 'Unknown')}"
        )

        forecast_lines = "\n".join(
            f"• **{f['appliance']}**: {f.get('predicted_kwh', '?'):.2f} kWh"
            for f in forecasts
        )

        simulated_note = ""
        if any(f.get("simulated") for f in forecasts):
            simulated_note = "\n\n_⚠️ Some predictions are simulated (ML models not loaded)_"

        confidence = "HIGH" if "Unknown" not in weather.get("condition", "Unknown") else "MEDIUM"
        probability = min(100, int(total_predicted * 5))

        reply = (
            f"📊 Usage Forecast Report\n\n"
            f"Tomorrow Forecast:\n"
            f"Temperature: {weather.get('temp_high', '?')}°C / {weather.get('temp_low', '?')}°C\n"
            f"Weather: {weather.get('condition', 'Unknown')}\n\n"
            f"Predicted Consumption: {total_predicted:.2f} kWh\n"
            f"Expected Cost: ₹{total_predicted * 12.0:.2f}\n"
            f"Peak Usage Window: 18:00 - 22:00\n\n"
            f"Risk Probability: {probability}%\n"
            f"Forecast Confidence: {confidence}"
        )

        return {
            "reply": reply,
            "active_agent": self.NAME,
            "risk_level": risk,
            "recommended_action": f"Prepare optimization plan for {total_predicted:.1f} kWh predicted load.",
            "data": {"weather": weather, "forecasts": forecasts}
        }
