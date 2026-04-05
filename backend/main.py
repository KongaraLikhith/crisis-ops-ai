import threading
import uuid
import asyncio
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 1. Import DB and Models
from models import db

load_dotenv()

# ── App setup ────────────────────────────────────────────
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)

db.init_app(app)

# 2. Import DB Tools (Now that the file exists!)
from tools.db_tools import (
    save_incident, agents_done, assign_incident,
    resolve_incident, get_incident, get_logs, list_incidents
)

# ── TRIGGER ENDPOINT ──────────────────────────────────────
@app.route("/api/incident/trigger", methods=["POST"])
def trigger_incident():
    data = request.get_json()
    title = data.get("title", "")
    description = data.get("description", "")

    if not title:
        return jsonify({"error": "title required"}), 400

    incident_id = "INC-" + str(uuid.uuid4())[:8].upper()

    # Save to DB immediately
    save_incident(incident_id, title, description)

    # Run agents in background - passing app_context is CRITICAL
    thread = threading.Thread(
        target=run_agents_background,
        args=(app.app_context(), incident_id, title, description)
    )
    thread.start()

    return jsonify({"incident_id": incident_id}), 201


def run_agents_background(app_context, incident_id, title, description):
    """Runs inside a thread — needs its own app context."""
    with app_context:
        asyncio.run(process_incident(incident_id, title, description))


async def process_incident(incident_id, title, description):
    """
    This is where your teammate will plug in Gemini.
    For now, we use MOCK functions so the app doesn't crash.
    """
    try:
        # Once teammate finishes agents/commander.py, uncomment these:
        # from agents.commander import classify_severity, run_all_agents
        # severity = await classify_severity(title, description)
        # results  = await run_all_agents(incident_id, title, description, severity)
        
        # MOCK DATA for testing until teammate is done:
        await asyncio.sleep(3) # Simulate AI thinking
        severity = "P1"
        results = {
            "triage_root_cause": "Mock Root Cause: Potential DB deadlocks.",
            "triage_resolution": "Mock Fix: Scaling connection pool.",
            "comms": "Mock Slack Message: Investigating P1 incident.",
            "docs": "Mock Post-mortem: Draft generated."
        }

        agents_done(
            incident_id,
            severity,
            results["triage_root_cause"],
            results["triage_resolution"],
            results["comms"],
            results["docs"]
        )
    except Exception as e:
        print(f"Error in background agents: {e}")


# ── ASSIGN & RESOLVE ─────────────────────────────────────
@app.route("/api/incident/<incident_id>/assign", methods=["PATCH"])
def assign(incident_id):
    data = request.get_json()
    developer = data.get("developer_name", "")
    if not developer:
        return jsonify({"error": "developer_name required"}), 400
    assign_incident(incident_id, developer)
    return jsonify({"status": "assigned", "assigned_to": developer})

@app.route("/api/incident/<incident_id>/resolve", methods=["PATCH"])
def resolve(incident_id):
    data = request.get_json()
    resolve_incident(
        incident_id,
        data.get("resolved_by"),
        data.get("agent_was_correct"),
        data.get("human_root_cause"),
        data.get("human_resolution")
    )
    return jsonify({"status": "resolved"})


# ── READ ENDPOINTS ───────────────────────────────────────
@app.route("/api/incident/<incident_id>", methods=["GET"])
def get_one(incident_id):
    inc = get_incident(incident_id)
    return jsonify(inc) if inc else jsonify({"error": "not found"}), 404

@app.route("/api/logs/<incident_id>", methods=["GET"])
def get_incident_logs(incident_id):
    return jsonify(get_logs(incident_id))

@app.route("/api/incidents", methods=["GET"])
def get_all():
    return jsonify(list_incidents())

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=8000)