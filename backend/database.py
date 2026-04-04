import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db():
    """Returns a database connection"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def run_query(sql, params=None, fetch=False):
    """Helper: run any SQL query"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    if fetch:
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    conn.commit()
    cur.close()
    conn.close()