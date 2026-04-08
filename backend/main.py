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
    get_kb_stats,
    get_logs,
    get_past_incidents_all,
    get_similarity_response,
    list_incidents,
    log_action,
    resolve_incident,
    save_incident,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Quota Mitigation (Rate Limiting) ──────────────────────
import asyncio
from google.adk.models.google_llm import Gemini

_original_generate = Gemini.generate_content_async

async def patched_generate_content_async(self, *args, **kwargs):
    # Add a 5 second sleep before every single AI request to stay under 15 RPM
    logger.info("[Quota] Sleeping 5s to stay under Free Tier limits...")
    await asyncio.sleep(5)
    async for event in _original_generate(self, *args, **kwargs):
        yield event

Gemini.generate_content_async = patched_generate_content_async

# ── App setup ────────────────────────────────────────────
app = Flask(__name__, static_folder='static')

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

APP_NAME = "crisisops"
VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:3000",
            ]
        }
    },
)

db.init_app(app)

with app.app_context():
    db.create_all()


def normalize_severity(value: str | None) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


def _get_runner():
    """
    Lazily import and build the ADK InMemoryRunner after app setup.
    """
    from google.adk.runners import InMemoryRunner
    from agents.commander import root_agent
    return InMemoryRunner(agent=root_agent, app_name="crisisops")


async def _run_pipeline(incident_id: str, title: str, description: str) -> dict:
    """
    Execute the full crisis workflow via the ADK runner and extract the
    structured outputs written to session state by each sub-agent.
    """
    from google.adk.sessions import InMemorySessionService
    import google.genai.types as types

    runner = _get_runner()
    session_service = runner.session_service

    report_text = (
        f"Title: {title}\n"
        f"Incident ID: {incident_id}\n"
        f"Description: {description}"
    )

    await session_service.create_session(
        app_name=APP_NAME,
        user_id="system",
        session_id=incident_id,
        state={
            "INCIDENT_REPORT": report_text,
            "INCIDENT_ID": incident_id,
            "INCIDENT_TITLE": title,
            # Pre-seed downstream keys so agent instruction templates never
            # raise KeyError if an upstream agent fails to write its output.
            "intake_summary": "",
            "triage_report": "",
            "comms_summary": "",
        },
    )

    from google.genai.types import Content, Part
    initial_message = Content(
        role="user",
        parts=[types.Part(text=report_text)],
    )

    final_state = {}
    async for event in runner.run_async(
        user_id="system",
        session_id=incident_id,
        new_message=initial_message,
    ):
        # Capture the final session state once the run completes
        if hasattr(event, "state"):
            final_state = event.state

    # If state wasn't emitted as an event, fetch it directly from the session
    if not final_state:
        stored = await session_service.get_session(
            app_name=runner.app_name,
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

    category = normalize_severity(
        triage.get("confirmed_severity") or final_state.get("CONFIRMED_SEVERITY")
    )

    return {
        "triage_root_cause": triage.get("summary") or final_state.get("triage_report", ""),
        "triage_resolution": triage.get("recommended_action", ""),
        "comms": comms.get("summary") or final_state.get("comms_summary", ""),
        "docs": docs.get("summary") or final_state.get("incident_document", ""),
        "category": category,
    }


def run_agents_background(incident_id: str, title: str, description: str):
    """Runs inside a daemon thread — creates its own event loop and app context."""
    logger.info("[Background] Starting agent pipeline for %s", incident_id)
    try:
        with app.app_context():
            results = asyncio.run(_run_pipeline(incident_id, title, description))
            category = normalize_severity(results.get("category"))

            agents_done(
                incident_id,
                category,
                results.get("triage_root_cause", ""),
                results.get("triage_resolution", ""),
                results.get("comms", ""),
                results.get("docs", ""),
                category,
            )
    except Exception as e:
        logger.error(
            "[ERROR] Background agent run failed for %s: %s",
            incident_id,
            str(e),
        )
        traceback.print_exc()


@app.route("/api/incident/trigger", methods=["POST"])
def trigger_incident():
    try:
        data = request.get_json() or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()

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
        return jsonify({"error": "failed to trigger incident", "details": str(e)}), 500


@app.route("/api/incident/<incident_id>/assign", methods=["PATCH"])
def assign(incident_id):
    try:
        data = request.get_json() or {}
        developer = (data.get("developer_name") or "").strip()

        if not developer:
            return jsonify({"error": "developer_name required"}), 400

        assign_incident(incident_id, developer)
        return jsonify({"status": "assigned", "assigned_to": developer})

    except Exception as e:
        logger.error("[ERROR] /api/incident/%s/assign failed: %s", incident_id, str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to assign incident", "details": str(e)}), 500


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
        logger.error("[ERROR] /api/incident/%s/resolve failed: %s", incident_id, str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to resolve incident", "details": str(e)}), 500


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
        return jsonify({"error": "failed to fetch incident", "details": str(e)}), 500


@app.route("/api/incident/<incident_id>/similar", methods=["GET"])
def get_similar(incident_id):
    try:
        return jsonify(get_similarity_response(incident_id))
    except Exception as e:
        logger.error("[ERROR] /api/incident/%s/similar failed: %s", incident_id, str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to fetch similar incidents", "details": str(e)}), 500


@app.route("/api/logs/<incident_id>", methods=["GET"])
def get_incident_logs(incident_id):
    try:
        return jsonify(get_logs(incident_id))

    except Exception as e:
        logger.error("[ERROR] /api/logs/%s failed: %s", incident_id, str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to fetch logs", "details": str(e)}), 500


@app.route("/api/incidents", methods=["GET"])
def get_all():
    try:
        return jsonify(list_incidents())

    except Exception as e:
        logger.error("[ERROR] /api/incidents failed: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to fetch incidents", "details": str(e)}), 500


@app.route("/api/past-incidents", methods=["GET"])
def get_past():
    try:
        return jsonify(get_past_incidents_all())

    except Exception as e:
        logger.error("[ERROR] /api/past-incidents failed: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to fetch past incidents", "details": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        return jsonify(get_kb_stats())
    except Exception as e:
        logger.error("[ERROR] /api/stats failed: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": "failed to fetch stats", "details": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ── Serve Frontend ─────────────────────────────────────
from flask import send_from_directory

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


if __name__ == "__main__":

    app.run(debug=False, port=8000)
