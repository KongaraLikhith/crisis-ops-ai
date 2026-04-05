from main import app
from tools.search_tool import search_similar_incidents

query = "tenant burst"

with app.app_context():  # ✅ this gives db.session access
    result = search_similar_incidents(query, limit=3)
    print(result)