import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parents[0]
sys.path.insert(0, str(ROOT))

from backend.agents.coordinator import route

test_cases = [
    "What is my current energy usage?",
    "Forecast tomorrow's energy consumption",
    "Recommend a plan to cut down my bill",
    "Show me current alerts",
    "Turn off the AC",
    "What can you do?"
]

print("Testing Intent Forms:")
for case in test_cases:
    print(f"\nUser: '{case}'")
    try:
        res = route(case, {})
        print("-" * 50)
        print(f"Agent Assigned: {res.get('active_agent', 'Unknown')}")
        print("-" * 50)
        print(res.get('reply', 'No Reply'))
        print("=" * 50)
    except Exception as e:
        print(f"Error: {e}")
