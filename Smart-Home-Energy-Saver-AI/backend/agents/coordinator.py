"""
backend/agents/coordinator.py
-------------------------------
Synervy AI – Coordinator Agent
Routes natural language messages to the appropriate specialist agent.
Implements adaptive intent understanding with free-form NL input support.
"""

import re
from datetime import datetime

from backend.agents.monitoring import MonitoringAgent
from backend.agents.prediction import PredictionAgent
from backend.agents.decision import DecisionAgent
from backend.agents.execution import ExecutionAgent
from backend.agents.notification import NotificationAgent
from backend import history_store


# Singleton agent instances
_monitoring = MonitoringAgent()
_prediction = PredictionAgent()
_decision = DecisionAgent()
_execution = ExecutionAgent()
_notification = NotificationAgent()

import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyCMNAqg5PNQA5m09cyJDYepoOuDLbShy0s")
_model = genai.GenerativeModel("gemini-2.5-flash")

# Map of intent strings to agent instances
INTENT_MAP = {
    "MONITORING": _monitoring,
    "PREDICTION": _prediction,
    "DECISION": _decision,
    "EXECUTION": _execution,
    "NOTIFICATION": _notification,
    "GENERAL": None
}

def _route_to_agent(message: str, context: dict):
    """Determine which agent should handle the message using Gemini."""
    prompt = f"""You are an intent classification system for a Smart Home Energy AI.
Analyze the following user message and classify it into exactly ONE of the following categories:

- MONITORING: Queries about current energy usage, status, hub data, live reading, or monitoring.
- PREDICTION: Queries about future energy consumption, forecasting, tomorrow's usage, predications.
- DECISION: Requests for optimization plans, recommendations, saving energy, reducing bills, scheduling.
- EXECUTION: Commands to turn devices on/off, start/stop actions, override settings, apply plans.
- NOTIFICATION: Queries about alerts, warnings, critical risks, emergency notifications.
- GENERAL: General greetings, asking for help, or asking about capabilities.

Reply ONLY with the exact category name (e.g., MONITORING, PREDICTION, DECISION, EXECUTION, NOTIFICATION, or GENERAL) and nothing else.

User Message: "{message}"
"""
    try:
        response = _model.generate_content(prompt)
        intent = response.text.strip().upper()
        # Ensure the intent generated is strictly one of the expected keys
        if intent not in INTENT_MAP:
            # Fallback to general or decision if ambiguous
            intent = "DECISION"
        return INTENT_MAP[intent]
    except Exception as e:
        print(f"Gemini routing error: {e}")
        # Fallback to decision agent in case of API failure
        return _decision


def route(message: str, context: dict) -> dict:
    """
    Main entry point. Routes message to correct agent
    and logs the interaction to history.
    """
    agent = _route_to_agent(message, context)

    if agent is None:
        # General greeting / capability overview
        reply = (
            "❓ Help & Capabilities\n\n"
            "This system can:\n"
            "• Monitor real-time energy usage\n"
            "• Predict future consumption\n"
            "• Detect overload risks\n"
            "• Optimize device schedules\n"
            "• Reduce electricity costs\n\n"
            "How to use:\n"
            "Click any sidebar option to generate a specific report."
        )
        result = {
            "reply": reply,
            "active_agent": "CoordinatorAgent",
            "risk_level": context.get("last_risk_level", "LOW"),
            "recommended_action": "Ask me anything about your energy system."
        }
    else:
        result = agent.handle(message, context)

    # Log to history
    history_store.add_entry(
        agent=result.get("active_agent", "CoordinatorAgent"),
        action=message[:120],
        risk_level=result.get("risk_level", "LOW"),
        approval_status="auto-approved",
        details={"response_preview": result.get("reply", "")[:200]}
    )

    return result
