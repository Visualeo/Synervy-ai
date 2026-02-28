"""
backend/agents/monitoring.py
-----------------------------
Synervy AI – Monitoring Agent
Reads current and historical energy hub data from CSV/simulation.
"""

import random
from datetime import datetime
from backend.services.energy_data import get_latest_usage, get_appliance_list
from backend.services.weather import get_tomorrow_weather


class MonitoringAgent:
    NAME = "MonitoringAgent"

    def handle(self, message: str, context: dict) -> dict:
        """Answer queries about current energy state."""
        usage = get_latest_usage()
        appliances = get_appliance_list()

        # Build a narrative summary of current usage
        usage_records = usage.get("usage", [])
        usage_date = usage.get("date", "today")
        source = usage.get("source", "csv")

        if usage_records:
            lines = []
            total_kwh = 0.0
            for rec in usage_records[:5]:
                app = rec.get("appliance", rec.get("appliance", "Unknown"))
                kwh = rec.get("kwh", rec.get("kwh_consumed", 0))
                try:
                    kwh = float(kwh)
                    total_kwh += kwh
                    lines.append(f"• {app}")
                except Exception:
                    lines.append(f"• {app}")

            # Risk based on total load
            risk = "LOW"
            if total_kwh > 15:
                risk = "HIGH"
            elif total_kwh > 10:
                risk = "MEDIUM"

            trend = "Stable"
            if total_kwh > 5: trend = "Increasing"

            narrative = (
                f"⚡ Energy Status Overview\n\n"
                f"Current Consumption: {total_kwh:.2f} kWh\n"
                f"Trend: {trend}\n"
                f"Peak Usage Time: 19:00\n"
                f"Estimated Cost Today: ₹{total_kwh * 12.0:.2f}\n"
                f"High Consumption Devices:\n"
                + "\n".join(lines) + "\n\n"
                f"System Risk Level: {risk}"
            )
        else:
            risk = "LOW"
            narrative = (
                "⚡ Energy Status Overview\n\n"
                "Current Consumption: 0.00 kWh\n"
                "Trend: Stable\n"
                "Peak Usage Time: None\n"
                "Estimated Cost Today: ₹0.00\n"
                "High Consumption Devices:\n"
                "• None\n\n"
                "System Risk Level: LOW"
            )

        # Risk based on total load
        risk = "LOW"
        if total_kwh > 15:
            risk = "HIGH"
        elif total_kwh > 10:
            risk = "MEDIUM"

        return {
            "reply": narrative,
            "active_agent": self.NAME,
            "risk_level": risk,
            "recommended_action": "Continue monitoring. Consider optimizing high-consumption appliances.",
            "data": usage
        }
