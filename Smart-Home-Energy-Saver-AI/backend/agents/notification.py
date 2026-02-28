"""
backend/agents/notification.py
--------------------------------
Synervy AI – Notification Agent
Generates user alerts, risk advisories, and system notifications.
"""

from datetime import datetime
import random


ALERT_TEMPLATES = {
    "CRITICAL": [
        "🚨 **CRITICAL ALERT**: Energy consumption has exceeded safe operational thresholds. Immediate intervention required.",
        "🚨 **CRITICAL**: Temperature spike detected — high-risk energy surge imminent. Activating emergency load shedding protocol.",
    ],
    "HIGH": [
        "⚠️ **HIGH RISK**: Elevated energy demand detected. Optimization actions are strongly recommended.",
        "⚠️ **WARNING**: Peak tariff period approaching. Consider deferring high-draw appliances.",
    ],
    "MEDIUM": [
        "🔔 **ADVISORY**: Moderate energy load detected. Consider scheduling non-essential appliances to off-peak hours.",
        "🔔 **NOTICE**: Weather conditions may increase cooling demand tomorrow.",
    ],
    "LOW": [
        "✅ **System Normal**: All energy parameters within optimal range. No immediate action required.",
        "✅ **STATUS**: Grid load is stable. Optimal conditions for energy-saving operations.",
    ]
}


class NotificationAgent:
    NAME = "NotificationAgent"

    def handle(self, message: str, context: dict) -> dict:
        """Generate contextual alert or notification."""
        risk_level = context.get("last_risk_level", "LOW")
        msg_lower = message.lower()

        if any(kw in msg_lower for kw in ["alert", "warn", "critical", "notify", "notification"]):
            # Generate a relevant alert
            templates = ALERT_TEMPLATES.get(risk_level, ALERT_TEMPLATES["LOW"])
            alert_msg = random.choice(templates)
            
            # Extract just the plain text for the issue formatting
            import re
            clean_issue = re.sub(r'[^a-zA-Z0-9\s.,-]', '', alert_msg).replace('CRITICAL ALERT', '').replace('HIGH RISK', '').replace('WARNING', '').replace('ADVISORY', '').replace('NOTICE', '').replace('System Normal', '').replace('STATUS', '').strip()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reply = (
                f"🚨 System Risk Alerts\n\n"
                f"1. [Severity: {risk_level}]\n"
                f"   Device: System Wide\n"
                f"   Issue: {clean_issue}\n"
                f"   Impact: Monitor network conditions.\n"
                f"   Suggested Immediate Action: Contact grid coordinator or apply emergency load reduction.\n\n"
                f"Overall System Risk Level: {risk_level}"
            )
        else:
            # General status notification
            templates = ALERT_TEMPLATES.get(risk_level, ALERT_TEMPLATES["LOW"])
            alert_msg = random.choice(templates)
            import re
            clean_issue = re.sub(r'[^a-zA-Z0-9\s.,-]', '', alert_msg).replace('CRITICAL ALERT', '').replace('HIGH RISK', '').replace('WARNING', '').replace('ADVISORY', '').replace('NOTICE', '').replace('System Normal', '').replace('STATUS', '').strip()

            reply = (
                f"🚨 System Risk Alerts\n\n"
                f"1. [Severity: {risk_level}]\n"
                f"   Device: System Wide\n"
                f"   Issue: {clean_issue}\n"
                f"   Impact: Routine monitoring recommended.\n"
                f"   Suggested Action: Acknowledge alert and review current optimization plan.\n\n"
                f"Overall System Risk Level: {risk_level}"
            )

        return {
            "reply": reply,
            "active_agent": self.NAME,
            "risk_level": risk_level,
            "recommended_action": "Acknowledge alert and review current optimization plan.",
            "data": {"alert_type": risk_level, "timestamp": datetime.now().isoformat()}
        }
