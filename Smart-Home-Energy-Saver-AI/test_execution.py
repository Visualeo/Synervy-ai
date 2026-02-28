import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parents[0]
sys.path.insert(0, str(ROOT))

from backend.agents.execution import ExecutionAgent

test_cases = [
    "turn the ac off please",
    "Set the living room heater to 20 degrees",
    "can you pause the washing machine",
    "dim the lights to 40%",
    "enable sleep mode on my computer"
]

print("Testing Execution Agent Parsing with Gemini:")
agent = ExecutionAgent()
for case in test_cases:
    print(f"\nUser: '{case}'")
    try:
        res = agent.handle(case, {})
        data = res.get("data", {})
        print(f"Parsed Device:  {data.get('device', 'Unknown')}")
        print(f"Parsed Command: {data.get('command', 'Unknown')}")
    except Exception as e:
        print(f"Error: {e}")
