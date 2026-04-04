from agents.base import get_llm
from tools.db_tools import log_action
from tools.search_tool import search_similar_incidents

async def run_triage(incident_id, title, description, severity):
    llm = get_llm()
    similar = search_similar_incidents(title + " " + description)
    log_action(incident_id, "Triage", "History searched", similar[:150])

    prompt = f"""You are an expert incident responder.

Incident: {title}
Description: {description}
Severity: {severity}

Similar past incidents from our history:
{similar}

Reply in this EXACT format, with these exact headers:

ROOT CAUSE:
[your root cause here in 1-2 sentences]

RESOLUTION STEPS:
1. [step one]
2. [step two]
3. [step three]

CONFIDENCE: [High / Medium / Low]"""

    result = llm.invoke(prompt)
    raw = result.content

    # Parse the two sections out
    root_cause  = _extract(raw, "ROOT CAUSE:",     "RESOLUTION STEPS:")
    resolution  = _extract(raw, "RESOLUTION STEPS:", "CONFIDENCE:")

    log_action(incident_id, "Triage", "Analysis complete",
               f"Root cause: {root_cause[:100]}")
    return {"root_cause": root_cause, "resolution": resolution}

def _extract(text, start_marker, end_marker):
    """Pull text between two markers."""
    try:
        start = text.index(start_marker) + len(start_marker)
        end   = text.index(end_marker)
        return text[start:end].strip()
    except ValueError:
        return text.strip()   # fallback: return everything