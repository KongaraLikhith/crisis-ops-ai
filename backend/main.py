import threading
import uuid
import traceback
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
CORS(app)
db.init_app(app)

# Create tables on first run if they don't exist
with app.app_context():
    db.create_all()

from tools.db_tools import (
    save_incident,
    agents_done,
    assign_incident,
    resolve_incident,
    get_incident,
    get_logs,
    list_incidents
)


# ── TRIGGER ──────────────────────────────────────────────
@app.route("/api/incident/trigger", methods=["POST"])
def trigger_incident():
    try:
        data = request.get_json() or {}
        title = data.get("title", "")
        description = data.get("description", "")

        if not title:
            return jsonify({"error": "title required"}), 400

        incident_id = "INC-" + str(uuid.uuid4())[:8].upper()

        save_incident(incident_id, title, description)

        # Run agents in a background thread so we return immediately
        thread = threading.Thread(
            target=run_agents_background,
            args=(incident_id, title, description),
            daemon=True
        )
        thread.start()

        return jsonify({"incident_id": incident_id}), 201

    except Exception as e:
        print(f"[ERROR] /api/incident/trigger failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "failed to trigger incident",
            "details": str(e)
        }), 500


def run_agents_background(incident_id, title, description):
    """Runs inside a thread — needs its own app context."""
    import asyncio
    try:
        with app.app_context():
            asyncio.run(process_incident(incident_id, title, description))
    except Exception as e:
        print(f"[ERROR] Background agent run failed for {incident_id}: {str(e)}")
        traceback.print_exc()


async def process_incident(incident_id, title, description):
    try:
        from agents.commander import classify_severity, run_all_agents

        severity = await classify_severity(incident_id, title, description)
        results = await run_all_agents(incident_id, title, description, severity)

        agents_done(
            incident_id,
            severity,
            results["triage_root_cause"],
            results["triage_resolution"],
            results["comms"],
            results["docs"],
            results.get("category")
        )

    except Exception as e:
        print(f"[ERROR] process_incident failed for {incident_id}: {str(e)}")
        traceback.print_exc()
        raise


# ── ASSIGN ───────────────────────────────────────────────
@app.route("/api/incident/<incident_id>/assign", methods=["PATCH"])
def assign(incident_id):
    try:
        data = request.get_json() or {}
        developer = data.get("developer_name", "")

        if not developer:
            return jsonify({"error": "developer_name required"}), 400

        assign_incident(incident_id, developer)
        return jsonify({"status": "assigned", "assigned_to": developer})

    except Exception as e:
        print(f"[ERROR] /api/incident/{incident_id}/assign failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "failed to assign incident",
            "details": str(e)
        }), 500


# ── RESOLVE ──────────────────────────────────────────────
@app.route("/api/incident/<incident_id>/resolve", methods=["PATCH"])
def resolve(incident_id):
    try:
        data = request.get_json() or {}

        resolved_by = data.get("resolved_by")
        agent_was_correct = data.get("agent_was_correct")
        human_root_cause = data.get("human_root_cause")
        human_resolution = data.get("human_resolution")

        if not resolved_by:
            return jsonify({"error": "resolved_by required"}), 400

        resolve_incident(
            incident_id,
            resolved_by,
            agent_was_correct,
            human_root_cause,
            human_resolution
        )

        return jsonify({"status": "resolved"})

    except Exception as e:
        print(f"[ERROR] /api/incident/{incident_id}/resolve failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "failed to resolve incident",
            "details": str(e)
        }), 500


# ── READ ENDPOINTS ───────────────────────────────────────
@app.route("/api/incident/<incident_id>", methods=["GET"])
def get_one(incident_id):
    try:
        inc = get_incident(incident_id)
        if not inc:
            return jsonify({"error": "not found"}), 404
        return jsonify(inc)

    except Exception as e:
        print(f"[ERROR] /api/incident/{incident_id} failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "failed to fetch incident",
            "details": str(e)
        }), 500


@app.route("/api/logs/<incident_id>", methods=["GET"])
def get_incident_logs(incident_id):
    try:
        return jsonify(get_logs(incident_id))

    except Exception as e:
        print(f"[ERROR] /api/logs/{incident_id} failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "failed to fetch logs",
            "details": str(e)
        }), 500


@app.route("/api/incidents", methods=["GET"])
def get_all():
    try:
        return jsonify(list_incidents())

    except Exception as e:
        print(f"[ERROR] /api/incidents failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "failed to fetch incidents",
            "details": str(e)
        }), 500


@app.route("/api/health", methods=["GET"])
def health():
    try:
        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"[ERROR] /api/health failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "health check failed",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=8000)