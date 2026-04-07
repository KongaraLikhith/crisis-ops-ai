# backend/seed.py
# Run manually only if needed:
# python seed.py

from datetime import datetime
from main import app
from models import db, PastIncident

SEED_DATA = [
    {
        "title": "DB connection pool exhausted",
        "description": "All app servers throwing too many connections error during traffic spike.",
        "severity": "P0",
        "category": "database_performance",
        "agent_root_cause": "Application connection pool likely too small for concurrent load.",
        "agent_resolution": "Increase connection pool size and restart app servers.",
        "agent_comms": "We are investigating elevated database connection failures impacting application availability.",
        "agent_postmortem": "Traffic surge combined with insufficient DB pool sizing caused connection starvation across application servers.",
        "human_root_cause": "SQLAlchemy pool_size was too low and a long-running analytics job held active connections.",
        "human_resolution": "Increased pool_size to 20 and max_overflow to 10, terminated stuck sessions, and restarted app servers.",
        "agent_was_correct": True,
        "resolution_confidence": "human_verified",
        "embedding": None,
    },
    {
        "title": "Auth service 500s after deploy",
        "description": "Login requests started failing immediately after production deployment.",
        "severity": "P1",
        "category": "authentication",
        "agent_root_cause": "Recent deploy introduced an authentication service regression.",
        "agent_resolution": "Roll back the latest deployment.",
        "agent_comms": "We are investigating login failures following a recent deployment.",
        "agent_postmortem": "Authentication errors began after deployment, indicating a likely environment or config regression.",
        "human_root_cause": "JWT_SECRET environment variable was missing in the new deployment environment.",
        "human_resolution": "Added JWT_SECRET to production secret store and redeployed the auth service.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
        "embedding": None,
    },
    {
        "title": "Stripe webhook timeouts",
        "description": "Payment processing delayed and order queue backlog increasing rapidly.",
        "severity": "P1",
        "category": "integrations",
        "agent_root_cause": "Stripe webhook latency or API rate limiting may be causing retries.",
        "agent_resolution": "Throttle webhook processing and reduce retry pressure.",
        "agent_comms": "We are investigating delayed payment processing caused by webhook delivery timeouts.",
        "agent_postmortem": "Webhook processing became unstable under backlog conditions, increasing timeout and retry rates.",
        "human_root_cause": "Background job queue was backed up, causing webhook handlers to exceed timeout thresholds.",
        "human_resolution": "Scaled job workers from 2 to 8 and added a DB index on orders.created_at.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
        "embedding": None,
    },
    {
        "title": "Redis cache eviction causing slow API responses",
        "description": "API latency spiked from 50ms to 4s across read-heavy endpoints.",
        "severity": "P1",
        "category": "cache",
        "agent_root_cause": "Redis memory pressure is evicting frequently accessed keys.",
        "agent_resolution": "Increase Redis maxmemory and stabilize cache hit ratio.",
        "agent_comms": "We are mitigating elevated API latency related to cache instability.",
        "agent_postmortem": "Cache hit ratio collapsed after Redis memory pressure caused eviction of hot keys.",
        "human_root_cause": "Redis maxmemory was too low, reducing cache hit rate to 12%.",
        "human_resolution": "Increased Redis maxmemory to 4GB and added cache warming during deploy.",
        "agent_was_correct": True,
        "resolution_confidence": "human_verified",
        "embedding": None,
    },
    {
        "title": "S3 image uploads failing",
        "description": "Users cannot upload profile pictures or file attachments.",
        "severity": "P1",
        "category": "storage",
        "agent_root_cause": "Object storage access policy or credentials may be invalid.",
        "agent_resolution": "Verify storage policy and rotate credentials if needed.",
        "agent_comms": "We are investigating failed file uploads affecting user media and attachments.",
        "agent_postmortem": "Upload failures were likely caused by infrastructure access or object storage policy drift.",
        "human_root_cause": "IAM role credentials expired after scheduled secret rotation.",
        "human_resolution": "Rotated IAM credentials, updated secrets in parameter store, and added expiry alerts.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
        "embedding": None,
    },
    {
        "title": "Email notifications not sending",
        "description": "Users are not receiving password reset or verification emails.",
        "severity": "P2",
        "category": "notifications",
        "agent_root_cause": "Email provider may be degraded or rate-limiting traffic.",
        "agent_resolution": "Check provider health and retry delayed messages.",
        "agent_comms": "Transactional email delivery is degraded for some account flows.",
        "agent_postmortem": "Email delivery failures were caused by exhausted provider quota without alerting or failover.",
        "human_root_cause": "Email provider API key hit monthly send quota and sending was blocked.",
        "human_resolution": "Upgraded provider plan and added usage alerts at 80% threshold.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
        "embedding": None,
    },
]


with app.app_context():
    try:
        db.create_all()

        existing = PastIncident.query.count()
        if existing > 0:
            print(f"Already have {existing} past incidents — skipping seed.")
        else:
            for row in SEED_DATA:
                pi = PastIncident(
                    **row,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(pi)

        db.session.commit()
        print(f"Seeded {len(SEED_DATA)} past incidents.")

        # ── Seed Runbooks ──
        RUNBOOKS = [
            {
                "title": "Database Outage Runbook",
                "incident_type": "database_performance",
                "steps_json": [
                    {"order": 1, "step": "Check Cloud SQL connection metrics"},
                    {"order": 2, "step": "Verify active connection count"},
                    {"order": 3, "step": "Scale connection pool in app config"},
                    {"order": 4, "step": "Restart impacted app instances"}
                ],
                "tags": "sql, connections, scaling"
            },
            {
                "title": "Auth Regression Runbook",
                "incident_type": "authentication",
                "steps_json": [
                    {"order": 1, "step": "Check recent deploy logs for config errors"},
                    {"order": 2, "step": "Verify JWT keys in Secret Manager"},
                    {"order": 3, "step": "Revert to previous stable tag"},
                    {"order": 4, "step": "Verify login health check"}
                ],
                "tags": "auth, jwt, deploy"
            }
        ]
        from models import Runbook, Contact
        for rb_data in RUNBOOKS:
            if not Runbook.query.filter_by(incident_type=rb_data["incident_type"]).first():
                db.session.add(Runbook(**rb_data))
        
        # ── Seed Contacts ──
        CONTACTS = [
            {"name": "DevOps On-Call", "team": "platform", "role": "On-Call Engineer", "gmail_address": "devops@example.com", "calendar_id": "primary"},
            {"name": "Security Lead", "team": "security", "role": "Incident Responder", "gmail_address": "security@example.com", "calendar_id": "primary"},
            {"name": "DBA Team", "team": "dba", "role": "Database Administrator", "gmail_address": "dba@example.com", "calendar_id": "primary"}
        ]
        for c_data in CONTACTS:
            if not Contact.query.filter_by(name=c_data["name"]).first():
                db.session.add(Contact(**c_data))

        db.session.commit()
        print("Seeded Runbooks and Contacts.")

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Seed failed: {str(e)}")
        raise