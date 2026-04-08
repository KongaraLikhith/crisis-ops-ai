import asyncio
import logging
import os
import threading
import traceback
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
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
    update_incident_status,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_NAME = "crisisops"
VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

if GOOGLE_SERVICE_ACCOUNT_FILE:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_SERVICE_ACCOUNT_FILE
    logger.info("[Startup] Google service account configured for Calendar integration")
else:
    logger.warning(
        "[Startup] GOOGLE_SERVICE_ACCOUNT_FILE not set; Calendar tool may not initialize correctly"
    )

from google.adk.models.google_llm import Gemini

_original_generate = Gemini.generate_content_async


async def patched_generate_content_async(self, *args, **kwargs):
    logger.info("[Quota] Sleeping 5s before model call")
    await asyncio.sleep(5)
    async for event in _original_generate(self, *args, **kwargs):
        yield event


Gemini.generate_content_async = patched_generate_content_async

try:
    from google.api_core.exceptions import ResourceExhausted as _ResourceExhaustedError
except Exception:
    _ResourceExhaustedError = Exception

try:
    from google.genai.errors import ClientError
except Exception:
    ClientError = Exception

app = Flask(__name__, static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
    from google.adk.runners import InMemoryRunner
    from agents.commander import crisis_workflow

    return InMemoryRunner(agent=crisis_workflow, app_name=APP_NAME)


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


async def _run_pipeline(incident_id: str, title: str, description: str) -> dict:
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
            "INCIDENT_DESCRIPTION": description,
            "INCIDENT_SEVERITY": DEFAULT_SEVERITY,
            "INCIDENT_STATUS": "processing",
            "PIPELINE_STATUS": "running",
            "SLACK_CHANNEL": "",
            "SLACK_CHANNEL_ID": "",
            "WAR_ROOM_LINK": "",
            "CALENDAR_EVENT_ID": "",
            "CALENDAR_EVENT_URL": "",
            "INCIDENT_DOC_URL": "",
            "INCIDENT_SHEET_URL": "",
            "TRIAGE_REPORT": {},
            "COMMS_SUMMARY": {},
            "INCIDENT_DOCUMENT": {},
            "RESOLUTION_NOTES": "",
        },
    )

    initial_message = types.Content(
        role="user",
        parts=[types.Part(text=report_text)],
    )

    final_state = {}
    async for event in runner.run_async(
        user_id="system",
        session_id=incident_id,
        new_message=initial_message,
    ):
        pass

    try:
        stored = await session_service.get_session(
            app_name=APP_NAME,
            user_id="system",
            session_id=incident_id,
        )
        final_state = stored.state if stored else {}
    except Exception as e:
        logger.error(
            "[Pipeline] Failed to fetch final session state for %s: %s",
            incident_id,
            e,
        )
        traceback.print_exc()
        return {"ok": False, "reason": "state_fetch_failed"}

    if not final_state:
        logger.warning("[Pipeline] No final state found for %s", incident_id)
        return {"ok": False, "reason": "no_final_state"}

    logger.info(
        "[Pipeline] Completed for %s. State keys: %s",
        incident_id,
        list(final_state.keys()),
    )

    triage = _safe_dict(final_state.get("TRIAGE_REPORT"))
    comms = _safe_dict(final_state.get("COMMS_SUMMARY"))
    docs = _safe_dict(final_state.get("INCIDENT_DOCUMENT"))

    logger.info("[Pipeline] TRIAGE_REPORT raw for %s: %r", incident_id, triage)
    logger.info("[Pipeline] COMMS_SUMMARY raw for %s: %r", incident_id, comms)
    logger.info("[Pipeline] INCIDENT_DOCUMENT raw for %s: %r", incident_id, docs)

    triage_root_cause = (triage.get("summary") or "").strip()
    triage_resolution = (triage.get("recommended_action") or "").strip()
    comms_summary = (comms.get("summary") or "").strip()
    docs_summary = (docs.get("summary") or "").strip()

    category = normalize_severity(
        triage.get("confirmed_severity")
        or final_state.get("CONFIRMED_SEVERITY")
        or final_state.get("INCIDENT_SEVERITY")
    )

    required_outputs_present = all([
        triage_root_cause,
        comms_summary,
        docs_summary,
    ])

    if not required_outputs_present:
        logger.warning(
            "[Pipeline] Missing outputs for %s | triage_summary=%s triage_reco=%s comms_summary=%s docs_summary=%s",
            incident_id,
            bool(triage_root_cause),
            bool(triage_resolution),
            bool(comms_summary),
            bool(docs_summary),
        )
        final_state["PIPELINE_STATUS"] = "incomplete"
        return {
            "ok": False,
            "reason": "no_agent_outputs",
            "triage_raw": triage,
            "comms_raw": comms,
            "docs_raw": docs,
            "state": final_state,
        }

    final_state["PIPELINE_STATUS"] = "completed"
    return {
        "ok": True,
        "triage_root_cause": triage_root_cause,
        "triage_resolution": triage_resolution,
        "comms": comms_summary,
        "docs": docs_summary,
        "category": category,
        "state": final_state,
    }


def run_agents_background(incident_id: str, title: str, description: str):
    logger.info("[Background] Starting agent pipeline for %s", incident_id)

    with app.app_context():
        try:
            log_action(
                incident_id,
                "agents",
                "pipeline_started",
                "Background workflow started",
            )

            results = asyncio.run(_run_pipeline(incident_id, title, description))

            if not results.get("ok"):
                reason = results.get("reason", "pipeline_incomplete")
                logger.warning("[Pipeline] Incomplete for %s: %s", incident_id, reason)

                if reason == "no_agent_outputs":
                    logger.warning(
                        "[Pipeline] Raw outputs for %s | triage=%r | comms=%r | docs=%r",
                        incident_id,
                        results.get("triage_raw", {}),
                        results.get("comms_raw", {}),
                        results.get("docs_raw", {}),
                    )

                log_action(incident_id, "agents", "pipeline_incomplete", reason)
                update_incident_status(incident_id, "processing")
                return

            category = normalize_severity(results.get("category"))

            log_action(
                incident_id,
                "triage_agent",
                "triage_completed",
                results.get("triage_root_cause", ""),
            )
            log_action(
                incident_id,
                "comms_agent",
                "comms_completed",
                results.get("comms", ""),
            )
            log_action(
                incident_id,
                "docs_agent",
                "docs_completed",
                results.get("docs", ""),
            )

            agents_done(
                incident_id=incident_id,
                severity=category,
                agent_root_cause=results.get("triage_root_cause", ""),
                agent_resolution=results.get("triage_resolution", ""),
                agent_comms=results.get("comms", ""),
                agent_postmortem=results.get("docs", ""),
                category=category,
            )

            log_action(incident_id, "agents", "agents_done", "All agent outputs saved")

        except (_ResourceExhaustedError, ClientError) as e:
            logger.error("[Quota] Gemini quota exhausted for %s: %s", incident_id, e)
            log_action(incident_id, "agents", "quota_exhausted", str(e))
            update_incident_status(incident_id, "processing")
            traceback.print_exc()

        except Exception as e:
            logger.error("[ERROR] Background agent run failed for %s: %s", incident_id, e)
            log_action(incident_id, "agents", "pipeline_failed", str(e))
            update_incident_status(incident_id, "processing")
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
        return jsonify(
            {"error": "failed to trigger incident", "details": str(e)}
        ), 500


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
        return jsonify(
            {"error": "failed to assign incident", "details": str(e)}
        ), 500


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
        return jsonify(
            {"error": "failed to resolve incident", "details": str(e)}
        ), 500


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
        return jsonify(
            {"error": "failed to fetch incident", "details": str(e)}
        ), 500


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
        return jsonify(
            {"error": "failed to fetch logs", "details": str(e)}
        ), 500


@app.route("/api/incidents", methods=["GET"])
def get_all():
    try:
        return jsonify(list_incidents())
    except Exception as e:
        logger.error("[ERROR] /api/incidents failed: %s", str(e))
        traceback.print_exc()
        return jsonify(
            {"error": "failed to fetch incidents", "details": str(e)}
        ), 500


@app.route("/api/past-incidents", methods=["GET"])
def get_past():
    try:
        return jsonify(get_past_incidents_all())
    except Exception as e:
        logger.error("[ERROR] /api/past-incidents failed: %s", str(e))
        traceback.print_exc()
        return jsonify(
            {"error": "failed to fetch past incidents", "details": str(e)}
        ), 500


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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=False, port=8000)