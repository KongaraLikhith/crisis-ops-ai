from backend.models import db, PastIncident
from backend.main import app

with app.app_context():
    verified = PastIncident.query.filter_by(resolution_confidence='human_verified').count()
    correct = PastIncident.query.filter_by(resolution_confidence='human_verified', agent_was_correct=True).count()
    total = PastIncident.query.count()
    print(f"Human verified: {verified}")
    print(f"Agent correct: {correct}")
    print(f"Total: {total}")
    if verified > 0:
        print(f"Accuracy: {int((correct / verified) * 100)}%")
    else:
        print("Accuracy: 0%")
