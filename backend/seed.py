# backend/seed.py
# Run this ONCE: python seed.py
from main import app
from models import db, PastIncident
from datetime import datetime

SEED_DATA = [
    {
        "title": "DB connection pool exhausted",
        "description": "All app servers throwing too many connections error",
        "severity": "P0",
        "category": "database",
        "agent_root_cause": "SQLAlchemy pool_size default of 5 too low",
        "agent_resolution": "Set pool_size=20 and restart app servers",
        "human_root_cause": "SQLAlchemy pool_size=5 insufficient. Analytics job held all connections.",
        "human_resolution": "Set pool_size=20, max_overflow=10. Killed stuck queries via pg_terminate_backend. Rolling restart.",
        "agent_was_correct": True,
        "resolution_confidence": "human_verified",
    },
    {
        "title": "Auth service 500s after deploy",
        "description": "Login broken for all users after deploy",
        "severity": "P1",
        "category": "auth",
        "agent_root_cause": "Code bug introduced in latest deploy",
        "agent_resolution": "Roll back the deploy",
        "human_root_cause": "JWT_SECRET env var missing in new deployment environment",
        "human_resolution": "Added JWT_SECRET to production secrets manager. Redeployed auth service.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
    },
    {
        "title": "Stripe webhook timeouts",
        "description": "Payment processing failing, order queue backing up",
        "severity": "P1",
        "category": "payments",
        "agent_root_cause": "Stripe API rate limit hit",
        "agent_resolution": "Reduce webhook frequency",
        "human_root_cause": "Background job queue backed up, webhooks exceeded 30s timeout",
        "human_resolution": "Scaled job workers from 2 to 8. Added DB index on orders.created_at.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
    },
    {
        "title": "Redis cache eviction causing slow API responses",
        "description": "API response times spiked from 50ms to 4000ms",
        "severity": "P1",
        "category": "cache",
        "agent_root_cause": "Redis maxmemory too low, evicting hot keys",
        "agent_resolution": "Increase Redis maxmemory",
        "human_root_cause": "Redis maxmemory set too low, cache hit rate dropped to 12%",
        "human_resolution": "Increased Redis maxmemory to 4GB. Added cache warming script on deploy.",
        "agent_was_correct": True,
        "resolution_confidence": "human_verified",
    },
    {
        "title": "S3 image uploads failing",
        "description": "Users cannot upload profile pictures or attachments",
        "severity": "P1",
        "category": "storage",
        "agent_root_cause": "S3 bucket policy changed",
        "agent_resolution": "Review and fix S3 bucket policy",
        "human_root_cause": "AWS IAM role credentials expired after 90-day rotation policy",
        "human_resolution": "Rotated IAM credentials. Updated secrets in parameter store. Added expiry alert.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
    },
    {
        "title": "Email notifications not sending",
        "description": "Users not receiving password reset and verification emails",
        "severity": "P2",
        "category": "email",
        "agent_root_cause": "Email service provider outage",
        "agent_resolution": "Wait for provider to recover",
        "human_root_cause": "SendGrid API key hit monthly send limit. No alerting configured.",
        "human_resolution": "Upgraded SendGrid plan. Added usage alert at 80% of monthly limit.",
        "agent_was_correct": False,
        "resolution_confidence": "human_verified",
    },
]

with app.app_context():
    db.create_all()
    existing = PastIncident.query.count()
    if existing > 0:
        print(f"Already have {existing} records — skipping seed.")
    else:
        for row in SEED_DATA:
            pi = PastIncident(**row, created_at=datetime.utcnow())
            db.session.add(pi)
        db.session.commit()
        print(f"Seeded {len(SEED_DATA)} past incidents.")