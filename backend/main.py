# backend/main.py
import threading
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db
from dotenv import load_dotenv
import os

load_dotenv()

# ── App setup ────────────────────────────────────────────
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)           # allow React (port 5173) to call this server
db.init_app(app)

# Create tables on first run if they don't exist
with app.app_context():
    db.create_all()

from tools.db_tools import (save_incident, agents_done, assign_incident,
                             resolve_incident, get_incident,
                             get_logs, list_incidents)


# ── TRIGGER ──────────────────────────────────────────────
@app.route("/api/incident/trigger", methods=["POST"])
def trigger_incident():
    data = request.get_json()
    title       = data.get("title", "")
    description = data.get("description", "")

    if not title:
        return jsonify({"error": "title required"}), 400

    incident_id = "INC-" + str(uuid.uuid4())[:8].upper()

    with app.app_context():
        save_incident(incident_id, title, description)

    # Run agents in a background thread so we return immediately
    thread = threading.Thread(
        target=run_agents_background,
        args=(incident_id, title, description)
    )
    thread.start()

    return jsonify({"incident_id": incident_id}), 201


def run_agents_background(incident_id, title, description):
    """Runs inside a thread — needs its own app context."""
    import asyncio
    with app.app_context():
        asyncio.run(process_incident(incident_id, title, description))


async def process_incident(incident_id, title, description):
    from agents.commander import classify_severity, run_all_agents
    severity = await classify_severity(title, description)
    results  = await run_all_agents(incident_id, title, description, severity)
    agents_done(
        incident_id,
        severity,
        results["triage_root_cause"],
        results["triage_resolution"],
        results["comms"],
        results["docs"]
    )


# ── ASSIGN ───────────────────────────────────────────────
@app.route("/api/incident/<incident_id>/assign", methods=["PATCH"])
def assign(incident_id):
    data = request.get_json()
    developer = data.get("developer_name", "")
    if not developer:
        return jsonify({"error": "developer_name required"}), 400
    assign_incident(incident_id, developer)
    return jsonify({"status": "assigned", "assigned_to": developer})


# ── RESOLVE ──────────────────────────────────────────────
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