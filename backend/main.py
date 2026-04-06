import asyncio
import logging
import os
import threading
import traceback
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from models import db
from tools.db_tools import (
    agents_done,
    assign_incident,
    get_incident,
    get_logs,
    get_past_incidents_all,
    list_incidents,
    log_action,
    resolve_incident,
    save_incident,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Allow local frontend + Cloud Shell previews
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:3000",
                # add your dev URL here if needed
            ]
        }
    },
)

db.init_app(app)

with app.app_context():
    db.create_all()


# ── ADK runner helper ────────────────────────────────────
def _get_runner():
    """
    Lazily imports and builds the ADK InMemoryRunner so the import
    only happens after the app context is fully initialised.
    """
    from google.adk.runners import InMemoryRunner
    from agents.commander import root_agent

    return InMemoryRunner(agent=root_agent)


async def _run_pipeline(incident_id: str, title: str, description: str) -> dict:
    """
    Execute the full crisis_workflow via the ADK runner and extract the
    structured outputs written to session state by each sub-agent.

    Returns a dict shaped like:
    {
      "triage_root_cause": str,
      "triage_resolution": str,
      "comms":             str,
      "docs":              str,
      "category":          str | None,
    }
    """
    from google.adk.sessions import InMemorySessionService
    import google.genai.types as types

    session_service = InMemorySessionService()
    runner = _get_runner()

    # Seed initial state so intake_agent picks it up via { INCIDENT_REPORT }
    report_text = (
        f"Title: {title}\n"
        f"Incident ID: {incident_id}\n"
        f"Description: {description}"
    )

    await session_service.create_session(
        app_name="crisisops",
        user_id="system",
        session_id=incident_id,
        state={"INCIDENT_REPORT": report_text},
    )

    initial_message = types.Content(
        role="user",
        parts=[types.Part(text=report_text)],
    )

    # Run the workflow, then fetch final state from the session
    async for _ in runner.run_async(
        user_id="system",
        session_id=incident_id,
        new_message=initial_message,
        session_service=session_service,
    ):
        pass

    stored = await session_service.get_session(
        app_name="crisisops",
        user_id="system",
        session_id=incident_id,
    )
    final_state = stored.state if stored else {}

    logger.info(
        "[Pipeline] Completed for %s. State keys: %s",
        incident_id,
        list(final_state.keys()),
    )

    triage: dict = final_state.get("TRIAGE_REPORT") or {}
    comms: dict = final_state.get("COMMS_SUMMARY") or {}
    docs: dict = final_state.get("INCIDENT_DOCUMENT") or {}

    return {
        "triage_root_cause": triage.get(
            "summary", final_state.get("triage_report", "")
        ),
        "triage_resolution": triage.get("recommended_action", ""),
        "comms": comms.get("summary", final_state.get("comms_summary", "")),
        "docs": docs.get("summary", final_state.get("incident_document", "")),
        "category": triage.get("confirmed_severity"),
    }


# ── Background thread entry point ───────────────────────
def run_agents_background(incident_id: str, title: str, description: str):
    """Runs inside a daemon thread — creates its own event loop and app context."""
    try:
        with app.app_context():
            results = asyncio.run(_run_pipeline(incident_id, title, description))
            agents_done(
                incident_id,
                results.get("category", "P3"),
                results["triage_root_cause"],
                results["triage_resolution"],
                results["comms"],
                results["docs"],
                results.get("category"),
            )
    except Exception as e:
        logger.error(
            "[ERROR] Background agent run failed for %s: %s", incident_id, str(e)
        )
        traceback.print_exc()


# ── API: TRIGGER ────────────────────────────────────────
@app.route("/api/incident/trigger", methods=["POST"])
def trigger_incident():
    try:
        data = request.get_json() or {}
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()

        if not title:
            return jsonify({"error": "title required"}), 400
        if not description:
            return jsonify({"error": "description required"}), 400

        incident_id = "INC-" + str(uuid.uuid4())[:8].upper()

        save_incident(incident_id, title, description)
        log_action(incident_id, "api", "incident_triggered", f"Title: {title}")

        thread = threading.Thread(
            target=run_agents_background,
            args=(incident_id, title, description),
            daemon=True,
        )
        thread.start()

        return jsonify({"incident_id": incident_id}), 201

    except Exception as e:
        logger.error("[ERROR] /api/incident/trigger failed: %s", str(e))
        traceback.print_exc()
        return (
            jsonify(
                {"error": "failed to trigger incident", "details": str(e)}
            ),
            500,
        )


# ── API: ASSIGN ─────────────────────────────────────────
@app.route("/api/incident/<incident_id>/assign", methods=["PATCH"])
def assign(incident_id):
    try:
        data = request.get_json() or {}
        developer = data.get("developer_name", "").strip()

        if not developer:
            return jsonify({"error": "developer_name required"}), 400

        assign_incident(incident_id, developer)
        return jsonify({"status": "assigned", "assigned_to": developer})

    except Exception as e:
        logger.error(
            "[ERROR] /api/incident/%s/assign failed: %s", incident_id, str(e)
        )
        traceback.print_exc()
        return (
            jsonify(
                {"error": "failed to assign incident", "details": str(e)}
            ),
            500,
        )


# ── API: RESOLVE ────────────────────────────────────────
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
            human_resolution,
        )
        return jsonify({"status": "resolved"})

    except Exception as e:
        logger.error(
            "[ERROR] /api/incident/%s/resolve failed: %s", incident_id, str(e)
        )
        traceback.print_exc()
        return (
            jsonify(
                {"error": "failed to resolve incident", "details": str(e)}
            ),
            500,
        )


# ── API: READ INCIDENTS & LOGS ──────────────────────────
@app.route("/api/incident/<incident_id>", methods=["GET"])
def get_one(incident_id):
    try:
        inc = get_incident(incident_id)
        if not inc:
            return jsonify({"error": "not found"}), 404
        return jsonify(inc)

    except Exception as e:
        logger.error("[ERROR] /api/incident/%s failed: %s", incident_id, str(e))
        traceback.print_exc()
        return (
            jsonify(
                {"error": "failed to fetch incident", "details": str(e)}
            ),
            500,
        )


@app.route("/api/logs/<incident_id>", methods=["GET"])
def get_incident_logs(incident_id):
    try:
        return jsonify(get_logs(incident_id))

    except Exception as e:
        logger.error("[ERROR] /api/logs/%s failed: %s", incident_id, str(e))
        traceback.print_exc()
        return (
            jsonify({"error": "failed to fetch logs", "details": str(e)}),
            500,
        )


@app.route("/api/incidents", methods=["GET"])
def get_all():
    try:
        return jsonify(list_incidents())

    except Exception as e:
        logger.error("[ERROR] /api/incidents failed: %s", str(e))
        traceback.print_exc()
        return (
            jsonify(
                {"error": "failed to fetch incidents", "details": str(e)}
            ),
            500,
        )


@app.route("/api/past-incidents", methods=["GET"])
def get_past():
    try:
        return jsonify(get_past_incidents_all())

    except Exception as e:
        logger.error("[ERROR] /api/past-incidents failed: %s", str(e))
        traceback.print_exc()
        return (
            jsonify(
                {"error": "failed to fetch past incidents", "details": str(e)}
            ),
            500,
        )


# ── API: HEALTH ─────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=8000)
