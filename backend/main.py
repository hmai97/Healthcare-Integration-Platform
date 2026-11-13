from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor

from app.api.routes.appointments import router as appointments_router
from app.api.routes.billing import router as billing_router
from app.api.routes.events import router as events_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.patients import router as patients_router
from app.kafka.consumer import HealthcareKafkaConsumer
from app.schemas.event import HealthResponse
from app.utils.logger import logger

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = HealthcareKafkaConsumer()
    consumer_task = None

    try:
        await consumer.start()
        consumer_task = asyncio.create_task(consumer.consume_forever())
    except Exception as exc:
        logger.error("Unable to connect to Kafka at %s: %s", consumer.bootstrap_servers, exc)

    try:
        yield
    finally:
        if consumer_task is not None:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        await consumer.stop()


app = FastAPI(lifespan=lifespan, title="Healthcare Integration Platform")
# lets the browser fetch from the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(events_router)
app.include_router(patients_router)
app.include_router(appointments_router)
app.include_router(billing_router)
app.include_router(monitoring_router)

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        cursor_factory=RealDictCursor,
    )

    conn.close()
    print("Database connection successful")

except Exception as e:
    print("Database connection failed")
    print("Error:", e)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "Welcome to Healthcare Integration!"}