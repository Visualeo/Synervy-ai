"""
backend/services/energy_data.py
---------------------------------
Energy data service – reads appliance usage CSV from the original project.
Original data source: Smart Home Energy Saver MAF (preserved attribution).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT_DIR / "data" / "appliance_usage.csv"

APPLIANCES = [
    "Air Conditioning",
    "Washing Machine",
    "Dishwasher",
    "Heater",
    "Computer",
]


def get_latest_usage() -> dict:
    """Returns the most recent day's usage data from CSV."""
    try:
        df = pd.read_csv(str(CSV_PATH), parse_dates=["date"])
        latest_date = df["date"].max()
        latest_records = df[df["date"] == latest_date].copy()
        latest_records["date"] = latest_records["date"].dt.strftime("%Y-%m-%d")
        latest_records["start_time"] = latest_records["start_time"].astype(str)
        latest_records["end_time"] = latest_records["end_time"].astype(str)
        return {
            "date": latest_date.strftime("%Y-%m-%d"),
            "usage": latest_records.to_dict(orient="records"),
            "source": "csv"
        }
    except Exception as e:
        # Graceful simulation fallback
        import random
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "usage": [
                {
                    "appliance": a,
                    "kwh": round(random.uniform(0.5, 5.0), 2),
                    "status": "active"
                }
                for a in APPLIANCES
            ],
            "source": "simulated",
            "error": str(e)
        }


def get_appliance_list() -> list[str]:
    return APPLIANCES
