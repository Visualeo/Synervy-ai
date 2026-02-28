"""
backend/agents/decision.py
----------------------------
Synervy AI – Decision Agent
Generates optimization decisions and personalized recommendations.
Core optimization logic adapted from Smart Home Energy Saver MAF (attribution preserved).
"""

from backend.services.optimizer import generate_optimization_plan


class DecisionAgent:
    NAME = "DecisionAgent"

    def handle(self, message: str, context: dict) -> dict:
        """Generate optimized energy plan with actionable recommendations."""
        plan = generate_optimization_plan(
            hh_size=context.get("hh_size", 4),
            latitude=context.get("latitude", 18.6298),
            longitude=context.get("longitude", 73.7997),
            timezone=context.get("timezone", "Asia/Kolkata"),
            rate_peak=context.get("rate_peak", 12.0),
            rate_offpeak=context.get("rate_offpeak", 7.5),
        )

        risk_level = plan.get("risk_level", "LOW")
        actions = plan.get("actions", [])
        total_kwh = plan.get("total_estimated_kwh_saving", 0)
        total_cost = plan.get("total_estimated_cost_saving_inr", 0)

        action_lines = "\n".join(
            f"• {a['appliance']}: {a['recommendation']} — (Save {a.get('estimated_kwh_saving', 0):.1f} kWh / ₹{a.get('estimated_cost_saving', 0):.1f})"
            for a in actions
        )

        reply = (
            f"⚡ Optimization Plan Ready\n\n"
            f"Simple Summary: {plan.get('summary', 'Optimization complete.')}\n"
            f"Weather Forecast: Normal conditions expected.\n"
            f"Potential Savings: {total_kwh:.2f} kWh (₹{total_cost:.2f})\n\n"
            f"Technical Breakdown & Actions:\n{action_lines}\n\n"
            f"Total Savings: {total_kwh:.2f} kWh (₹{total_cost:.2f})\n"
            f"System Risk Level: {risk_level}"
        )

        return {
            "reply": reply,
            "active_agent": self.NAME,
            "risk_level": risk_level,
            "recommended_action": f"Apply {len(actions)} optimization actions to save {total_kwh:.2f} kWh.",
            "data": plan
        }
