from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
from tools.db_tools import (save_incident, agents_done, assign_incident,
                             resolve_incident, get_incident,
                             get_logs, list_incidents)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── REQUEST BODIES ───────────────────────────────────────
class TriggerRequest(BaseModel):
    title: str
    description: str

class AssignRequest(BaseModel):
    developer_name: str       # e.g. "Rahul" or "rahul@team.com"

class ResolveRequest(BaseModel):
    resolved_by: str
    agent_was_correct: bool   # did the agent's root cause match reality?
    human_root_cause: Optional[str] = None   # fill if agent was wrong
    human_resolution: str     # what steps actually fixed it

# ── ENDPOINTS ────────────────────────────────────────────
@app.post("/api/incident/trigger")
async def trigger(req: TriggerRequest, bg: BackgroundTasks):
    incident_id = "inc-" + str(uuid.uuid4())[:8]
    save_incident(incident_id, req.title, req.description)
    bg.add_task(process_incident, incident_id, req.title, req.description)
    return {"incident_id": incident_id}

@app.patch("/api/incident/{incident_id}/assign")
def assign(incident_id: str, req: AssignRequest):
    assign_incident(incident_id, req.developer_name)
    return {"status": "assigned", "assigned_to": req.developer_name}

@app.patch("/api/incident/{incident_id}/resolve")
def resolve(incident_id: str, req: ResolveRequest):
    # If agent was correct, reuse its root cause
    root_cause = req.human_root_cause if not req.agent_was_correct else None
    resolve_incident(
        incident_id,
        req.resolved_by,
        req.agent_was_correct,
        root_cause,
        req.human_resolution
    )
    return {"status": "resolved"}

@app.get("/api/incident/{incident_id}")
def get_one(incident_id: str):
    inc = get_incident(incident_id)
    return inc if inc else {"status": "not_found"}

@app.get("/api/logs/{incident_id}")
def get_incident_logs(incident_id: str):
    return get_logs(incident_id)

@app.get("/api/incidents")
def get_all():
    return list_incidents()

# ── BACKGROUND TASK ──────────────────────────────────────
async def process_incident(incident_id, title, description):
    from agents.commander import classify_severity, run_all_agents
    severity = await classify_severity(title, description)
    results  = await run_all_agents(incident_id, title, description, severity)
    agents_done(
        incident_id, severity,
        results["triage_root_cause"],
        results["triage_resolution"],
        results["comms"],
        results["docs"]
    )