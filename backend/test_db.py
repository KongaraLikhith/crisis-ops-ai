import os
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv

load_dotenv()

# Instead of passing the whole string to create_engine, 
# we build a URL object which handles the "@" automatically.
url_object = URL.create(
    drivername="postgresql",
    username="postgres",
    password="24VaYOhV9QSmZbMm@",  # You can pull this from os.getenv("DB_PASS")
    host="db.dwggagcfzwhxswaelbqt.supabase.co",
    port=5432,
    database="postgres"
)

engine = create_engine(url_object)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("DB Connected:", result.scalar())