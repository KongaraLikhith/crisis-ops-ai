import asyncio
from agents.base import get_llm
from tools.db_tools import log_action

async def classify_severity(title, description):
    llm = get_llm()
    prompt = f"""Classify this incident as P0, P1, or P2. Reply with ONLY those 3 characters.
P0 = everything down, all users affected
P1 = major feature broken, many users affected
P2 = minor issue, few users affectede
Incident: {title}
Description: {description}"""
    result = llm.invoke(prompt)
    severity = result.content.strip()[:2]   # safety trim
    log_action("system", "Commander", "Severity classified", severity)
    return severity

async def run_all_agents(incident_id, title, description, severity):
    from agents.triage    import run_triage
    from agents.comms     import run_comms
    from agents.docs_agent import run_docs

    triage_result, comms_result, docs_result = await asyncio.gather(
        run_triage(incident_id, title, description, severity),
        run_comms(incident_id, title, severity),
        run_docs(incident_id, title, severity),
    )
    # triage returns a dict with root_cause + resolution separate
    return {
        "triage_root_cause": triage_result["root_cause"],
        "triage_resolution": triage_result["resolution"],
        "comms":             comms_result,
        "docs":              docs_result,
    }
