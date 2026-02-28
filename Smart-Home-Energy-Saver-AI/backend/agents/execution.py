"""
backend/agents/execution.py
-----------------------------
Synervy AI – Execution Agent
Simulates control commands sent to energy devices (AC, lights, etc.).
"""

import json
from datetime import datetime
import google.generativeai as genai

genai.configure(api_key="AIzaSyCMNAqg5PNQA5m09cyJDYepoOuDLbShy0s")
_model = genai.GenerativeModel("gemini-2.5-flash")

EXECUTION_RESULTS = [
    "✅ Command acknowledged by device controller.",
    "✅ Device responded — action applied successfully.",
    "✅ Control signal dispatched to hub.",
]


class ExecutionAgent:
    NAME = "ExecutionAgent"
    _log: list = []

    def handle(self, message: str, context: dict) -> dict:
        """Simulate executing a control action on an energy device."""
        
        prompt = f"""Extract the target device and the specific command from this smart home request: "{message}"
Return ONLY valid JSON format with keys "device" and "command". If device is not explicit, use "system".
Do not include markdown formatting like ```json.
Example: {{"device": "AC", "command": "Turn off AC"}}."""

        detected_device = "System"
        cmd = "Apply general power-saving profile to all connected devices"

        try:
            response = _model.generate_content(prompt)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_text)
            detected_device = data.get("device", "System")
            cmd = data.get("command", message)  # Fallback to full message if no command matched
        except Exception as e:
            print(f"Gemini parsing error in ExecutionAgent: {e}")
            # Fallback to basic string matching if Gemini fails
            devices = ["ac", "heater", "washing machine", "dishwasher", "computer", "lights"]
            msg_lower = message.lower()
            for device in devices:
                if device in msg_lower:
                    detected_device = device.title()
                    cmd = message.strip()
                    break

        import random
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = random.choice(EXECUTION_RESULTS)

        self._log.append({
            "timestamp": timestamp,
            "device": detected_device,
            "command": cmd,
            "result": result
        })

        reply = (
            f"🔌 Device Control Panel\n\n"
            f"Device: {detected_device}\n"
            f"Status: ON\n"
            f"Current Usage: 1.20 kWh\n"
            f"Recommendation: {cmd}\n"
            f"Schedule Suggestion: Apply settings immediately to maintain comfort while saving energy."
        )

        return {
            "reply": reply,
            "active_agent": self.NAME,
            "risk_level": "LOW",
            "recommended_action": "Monitor device response and confirm state change via feed.",
            "data": {"command": cmd, "device": detected_device, "timestamp": timestamp}
        }

    def get_log(self) -> list:
        return list(reversed(self._log[-20:]))
