import os
from flask import Flask
from models import db, Incident
from tools.db_tools import get_incident
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db.init_app(app)

with app.app_context():
    data = get_incident('INC-619F9245')
    print(f"INCIDENT DATA: {data}")
