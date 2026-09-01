"""Kafka producer placeholder for healthcare events."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaProducer

from app.kafka.config import settings
from app.kafka.topics import TOPICS, resolve_topic
from app.utils.logger import logger


def serialize_event(event: Mapping[str, Any] | Any) -> bytes:
    if hasattr(event, "model_dump"):
        payload = event.model_dump(mode="json")
    elif isinstance(event, Mapping):
        payload = dict(event)
    else:
        raise TypeError("Kafka event must be a mapping or Pydantic model")

    return json.dumps(payload, default=str).encode("utf-8")


def build_deadletter_message(event: Mapping[str, Any] | Any, error: str) -> dict[str, Any]:
    payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
    return {
        "event": payload,
        "error": error,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }


class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str | None = None):
        self.bootstrap_servers = bootstrap_servers or settings.bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id="healthcare-event-producer",
            )
            await self._producer.start()
            logger.info("KAFKA_CONNECTED broker=%s", self.bootstrap_servers)
        except Exception as exc:  # pragma: no cover - exercised via mocks in tests
            logger.error("Unable to connect to Kafka at %s: %s", self.bootstrap_servers, exc)
            raise

    async def publish_event(self, event: Mapping[str, Any] | Any, *, topic: str | None = None) -> str:
        await self.start()
        event_payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
        topic_name = topic or resolve_topic(event_payload.get("event_type"))
        event_id = str(event_payload.get("event_id", "unknown"))
        key = event_id.encode("utf-8")
        value = serialize_event(event_payload)

        try:
            await self._producer.send_and_wait(topic_name, key=key, value=value)
            logger.info(
                "EVENT_PUBLISHED event_id=%s event_type=%s topic=%s",
                event_id,
                event_payload.get("event_type"),
                topic_name,
            )
            return topic_name
        except Exception as exc:
            logger.error(
                "EVENT_PUBLISH_FAILED event_id=%s event_type=%s topic=%s error=%s",
                event_id,
                event_payload.get("event_type"),
                topic_name,
                exc,
            )
            raise

    async def publish_deadletter(self, event: Mapping[str, Any] | Any, error: str | None = None) -> str:
        if hasattr(event, "model_dump"):
            payload = event.model_dump(mode="json")
        elif isinstance(event, Mapping):
            payload = dict(event)
        else:
            payload = {"raw_message": str(event)}

        deadletter_message = build_deadletter_message(payload, error or "validation failed")
        await self.start()
        event_id = str(payload.get("event_id", "unknown")) if isinstance(payload, dict) else "unknown"
        key = event_id.encode("utf-8")
        value = json.dumps(deadletter_message, default=str).encode("utf-8")

        try:
            await self._producer.send_and_wait(TOPICS["deadletter"], key=key, value=value)
            logger.info("EVENT_SENT_TO_DEADLETTER event_id=%s", event_id)
            return TOPICS["deadletter"]
        except Exception as exc:
            logger.error("DEADLETTER_PUBLISH_FAILED event_id=%s error=%s", event_id, exc)
            raise

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("KAFKA_DISCONNECTED")


async def check_kafka_connectivity(bootstrap_servers: str | None = None) -> bool:
    client = KafkaProducerClient(bootstrap_servers=bootstrap_servers)
    try:
        await client.start()
        return True
    except Exception:
        return False
    finally:
        if client._producer is not None:
            await client.close()


producer_client = KafkaProducerClient()
