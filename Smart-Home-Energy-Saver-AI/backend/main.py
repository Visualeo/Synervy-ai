"""
backend/main.py
----------------
Synervy AI – Autonomous Energy Intelligence System
FastAPI application entry point.

Exposes:
  POST /chat            → Main conversational AI endpoint (multi-agent routing)
  GET  /history         → Optimization history log
  POST /history/{id}/approve  → Approve a history entry
  GET  /agents/activity → Real-time simulated agent activity feed
  GET  /health          → Health check
  Static /             → Serves the frontend at frontend/index.html

Original endpoints from Smart Home Energy Saver MAF are preserved below.
"""

import sys
import os
from pathlib import Path

# Ensure the parent directory is on the path so `backend.*` imports work
ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
import random

from backend.agents.coordinator import route
from backend import history_store
from backend.services.optimizer import generate_optimization_plan
from backend.agents.email_agent import generate_email_and_send_async

# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(
    title="Synervy AI – Autonomous Energy Intelligence System",
    description=(
        "Enterprise-grade multi-agent AI platform for autonomous energy management. "
        "Powered by Microsoft Agent Framework (MAF) — Smart Home Energy Saver core preserved."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    context: dict = {}

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "What is my current energy usage?",
                "context": {"hh_size": 4, "latitude": 18.6298, "longitude": 73.7997}
            }
        }
    }


class ChatResponse(BaseModel):
    reply: str
    active_agent: str
    risk_level: str
    recommended_action: str
    timestamp: str
    data: dict = {}


class ApprovalRequest(BaseModel):
    status: str  # "approved" | "rejected"


class OptimizeRequest(BaseModel):
    hh_size: int
    appliances_present: list[str] = []
    latitude: float
    longitude: float
    timezone: str
    rate_peak: float
    rate_offpeak: float
    tariff_peak_start: str = "18:00"
    tariff_peak_end: str = "22:00"


class EmailRequest(BaseModel):
    plan_json: dict
    email: str
    name: str = "User"


# ─────────────────────────────────────────────
# Session context (simple in-memory per instance)
# ─────────────────────────────────────────────
_session_context: dict = {
    "hh_size": 4,
    "latitude": 18.6298,
    "longitude": 73.7997,
    "timezone": "Asia/Kolkata",
    "rate_peak": 12.0,
    "rate_offpeak": 7.5,
    "last_risk_level": "LOW",
}


# ─────────────────────────────────────────────
# Simulated Agent Activity Feed
# ─────────────────────────────────────────────
ACTIVITY_TEMPLATES = [
    ("MonitoringAgent", "Polling energy hub data", "LOW"),
    ("PredictionAgent", "Running Prophet forecast model", "LOW"),
    ("DecisionAgent", "Evaluating optimization opportunities", "MEDIUM"),
    ("ExecutionAgent", "Standby — awaiting control commands", "LOW"),
    ("NotificationAgent", "Monitoring risk thresholds", "LOW"),
    ("CoordinatorAgent", "Routing incoming intents", "LOW"),
]


def get_live_activity(n: int = 6) -> list[dict]:
    """Returns simulated real-time agent activity."""
    now = datetime.now()
    activities = []
    for i, (agent, action, risk) in enumerate(ACTIVITY_TEMPLATES):
        activities.append({
            "agent": agent,
            "action": action,
            "risk_level": risk,
            "timestamp": now.strftime("%H:%M:%S"),
            "status": "active" if random.random() > 0.3 else "idle"
        })
    return activities


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "Synervy AI", "version": "1.0.0", "timestamp": datetime.now().isoformat()}


@app.post("/chat", response_model=ChatResponse, tags=["AI Chat"])
def chat(req: ChatRequest):
    """
    Main conversational endpoint. Routes message to the appropriate agent
    and returns a structured response with agent attribution and risk level.
    """
    try:
        # Merge request context with session context
        ctx = {**_session_context, **req.context}
        result = route(req.message, ctx)

        # Update session with latest risk level
        _session_context["last_risk_level"] = result.get("risk_level", "LOW")

        return ChatResponse(
            reply=result.get("reply", "I'm processing your request."),
            active_agent=result.get("active_agent", "CoordinatorAgent"),
            risk_level=result.get("risk_level", "LOW"),
            recommended_action=result.get("recommended_action", ""),
            timestamp=datetime.now().isoformat(),
            data=result.get("data", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent routing error: {e}")


@app.post("/optimize-energy", tags=["Optimization"])
def optimize_energy(req: OptimizeRequest):
    try:
        plan = generate_optimization_plan(
            hh_size=req.hh_size,
            latitude=req.latitude,
            longitude=req.longitude,
            timezone=req.timezone,
            rate_peak=req.rate_peak,
            rate_offpeak=req.rate_offpeak
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/email-plan", tags=["Notification"])
async def email_plan(req: EmailRequest):
    try:
        res = await generate_email_and_send_async(req.plan_json, req.email, req.name)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", tags=["History"])
def get_history(limit: int = 50):
    """Returns the optimization history log."""
    return {"history": history_store.get_history(limit), "count": limit}


@app.post("/history/{entry_id}/approve", tags=["History"])
def approve_history(entry_id: str, req: ApprovalRequest):
    """Update approval status of a history entry."""
    ok = history_store.update_approval(entry_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"status": "updated", "entry_id": entry_id, "approval_status": req.status}


@app.get("/agents/activity", tags=["Agents"])
def agents_activity():
    """Returns real-time simulated agent activity feed."""
    return {"activity": get_live_activity(), "timestamp": datetime.now().isoformat()}


@app.post("/context", tags=["System"])
def update_context(ctx: dict):
    """Update the session context (household size, tariff, location, etc.)."""
    _session_context.update(ctx)
    return {"status": "ok", "context": _session_context}


@app.get("/context", tags=["System"])
def get_context():
    """Get the current session context."""
    return _session_context


# ─────────────────────────────────────────────
# Static Frontend Serving
# ─────────────────────────────────────────────
STATIC_DIR = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if TEMPLATES_DIR.exists():
    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str = ""):
        index = TEMPLATES_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"message": "Synervy AI API running. Frontend not found.", "status": 404})


# ─────────────────────────────────────────────
# Local Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
