from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        cursor_factory=RealDictCursor
    )

    cursor = conn.cursor()
    print("Database connection successful")

except Exception as e:
    print("Database connection failed")
    print("Error:", e)


@app.get("/")
def home():
    return {"message": "Welcome to Healthcare Integration!"}