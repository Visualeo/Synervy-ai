"""
email_agent.py
---------------
Generates a human-friendly email report using Microsoft Agent Framework (Azure OpenAI)
and sends it via SMTP.

Run:
    python email_agent.py
"""

import json
import smtplib
import asyncio
from email.mime.text import MIMEText
from functools import lru_cache

from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

# -------------------------------
# SMTP CONFIG — replace with your own
# -------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "your-email-id"          # <-- CHANGE
EMAIL_PASSWORD = "your-email-token"      # <-- CHANGE (Gmail App Password)


def get_email_agent():
    """
    Create and cache a lightweight email-formatting agent.
    Using MAF agent.run avoids low-level message object quirks.
    """
    client = AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        deployment="gpt-4o-mini"  # ensure this deployment exists in your Azure OpenAI resource
    )

    instructions = """
    You are an Email Formatter for a Home Energy Optimizer.

    TASK:
    - Convert a given JSON energy-saving plan into a concise, friendly email.
    - Include greeting with recipient's name (provided separately).
    - Summarize weather/overall context from 'summary' when present.
    - List each recommendation with appliance, setting/action, and estimated savings (kWh and cost with currency).
    - Keep formatting readable in plain text; emojis are allowed but avoid HTML.
    - DO NOT include any sign-off, closing, or thank-you message. The system will append that automatically.

    OUTPUT:
    - Return ONLY the email body text (no signature, no JSON, no code fences).
    """


    return client.create_agent(instructions=instructions)


async def generate_email_body_async(plan_json: dict, recipient_name: str = "User") -> str:
    """
    Uses the MAF agent to transform plan JSON into a plain-text email body.
    """
    agent = get_email_agent()
    payload = {
        "recipient_name": recipient_name,
        "plan_json": plan_json,
    }
    # Give the model clear, single-turn input
    user_prompt = (
        "Format this energy-saving plan into an email.\n\n"
        f"Recipient: {recipient_name}\n\n"
        f"Plan JSON:\n{json.dumps(plan_json, indent=2)}\n\n"
        "Return plain text email only."
    )
    result = await agent.run(user_prompt)
    email_body = (result.text or "").strip()

    # Append branded signature
    signature = "\n\nBest regards,\nHome Energy Saver AI Agent 🤖"
    return email_body + signature



# -------------------------------
# SMTP SEND
# -------------------------------
def send_email(subject: str, body: str, recipient: str):
    """
    Sends a plain text email via SMTP.
    """
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, [recipient], msg.as_string())


# -------------------------------
# ONE-CALL API for FastAPI
# -------------------------------
async def generate_email_and_send_async(plan_json: dict, to_email: str, recipient_name: str = "User") -> dict:
    """
    Generate the email with LLM and send it via SMTP.
    """
    body = await generate_email_body_async(plan_json, recipient_name=recipient_name)
    subject = "Your Home Energy Optimization Report"
    send_email(subject, body, to_email)
    return {"status": "sent", "email": to_email}



# -------------------------------
# LOCAL TEST
# -------------------------------
if __name__ == "__main__":
    # Sample plan JSON (your provided example)
    sample_plan = {
        "summary": "⚠️ Tomorrow will be cooler than average with temperatures between 14.9°C and 26.9°C, providing an opportunity to optimize energy usage.",
        "actions": [
            {
                "appliance": "Air Conditioning",
                "recommendation": "Set to 24°C and use it only between 1PM–5PM.",
                "estimated_kwh_saving": 1.7,
                "estimated_cost_saving": 18.5,
                "currency": "INR"
            },
            {
                "appliance": "Washing Machine",
                "recommendation": "Run during off-peak hours (8PM–10PM) to wash full loads.",
                "estimated_kwh_saving": 0.2,
                "estimated_cost_saving": 2.2,
                "currency": "INR"
            },
            {
                "appliance": "Dishwasher",
                "recommendation": "Run on a shorter cycle during off-peak hours (8PM–10PM).",
                "estimated_kwh_saving": 0.2,
                "estimated_cost_saving": 2.2,
                "currency": "INR"
            },
            {
                "appliance": "Microwave",
                "recommendation": "Limit use to essential cooking for a maximum of 10 minutes between 5PM–7PM.",
                "estimated_kwh_saving": 0.1,
                "estimated_cost_saving": 1.1,
                "currency": "INR"
            },
            {
                "appliance": "Computer",
                "recommendation": "Schedule active use for only 3 hours (6PM–9PM).",
                "estimated_kwh_saving": 0.4,
                "estimated_cost_saving": 4.4,
                "currency": "INR"
            }
        ]
    }

    async def _demo():
        to_email = "your-email-id"  # <-- CHANGE
        print(f"Sending test email to {to_email}...")
        res = await generate_email_and_send_async(sample_plan, to_email, recipient_name="Sandesh")
        print("Result:", res)

    asyncio.run(_demo())
