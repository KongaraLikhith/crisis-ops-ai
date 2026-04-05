from main import app
from models import db, PastIncident
from datetime import datetime
from sqlalchemy import text

SEED_DATA = [
    {
        "title": "DB connection pool exhausted",
        "description": "All app servers throwing too many connections error",
        "severity": "P0",
        "category": "database",
        "agent_root_cause": "SQLAlchemy pool_size default of 5 too low",
        "agent_resolution": "Set pool_size=20 and restart app servers",
        "human_root_cause": "SQLAlchemy pool_size=5 insufficient. Analytics job held all connections.",
        "human_resolution": "Set pool_size=20, max_overflow=10. Killed stuck queries via pg_terminate_backend.",
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
    }
]

with app.app_context():
    # 1. Enable the vector extension FIRST and commit it
    db.session.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    db.session.commit()
    print("pgvector extension enabled.")

    # 2. NOW create the tables
    db.create_all()
    print("Tables created.")

    # 3. Seed the data
    existing = PastIncident.query.count()
    if existing > 0:
        print(f"Already have {existing} records — skipping seed.")
    else:
        for row in SEED_DATA:
            pi = PastIncident(**row, created_at=datetime.utcnow())
            db.session.add(pi)
        db.session.commit()
        print(f"Seeded {len(SEED_DATA)} past incidents successfully!")