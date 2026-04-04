import os
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("DB Connected:", result.scalar())
