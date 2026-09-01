"""Kafka consumer placeholder for healthcare events."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer

from app.core.database import SessionLocal
from app.kafka.config import settings
from app.kafka.producer import KafkaProducerClient, build_deadletter_message
from app.kafka.topics import TOPICS
from app.models.event import EventStatus
from app.repositories.event_repository import EventRepository
from app.services.event_processor import EventProcessingService
from app.services.validation_service import ValidationService
from app.utils.logger import logger


class HealthcareKafkaConsumer:
    def __init__(
        self,
        bootstrap_servers: str | None = None,
        group_id: str | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or settings.bootstrap_servers
        self.group_id = group_id or settings.group_id
        self.consumer: AIOKafkaConsumer | None = None
        self.producer = KafkaProducerClient(bootstrap_servers=self.bootstrap_servers)
        self.event_repository = EventRepository()
        self.event_processor = EventProcessingService()

    async def start(self) -> None:
        if self.consumer is not None:
            return
        try:
            self.consumer = AIOKafkaConsumer(
                TOPICS["patients"],
                TOPICS["appointments"],
                TOPICS["billing"],
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            await self.consumer.start()
            logger.info(
                "KAFKA_CONNECTED group_id=%s topics=%s",
                self.group_id,
                [TOPICS["patients"], TOPICS["appointments"], TOPICS["billing"]],
            )
        except Exception as exc:
            logger.error("Unable to connect to Kafka at %s: %s", self.bootstrap_servers, exc)
            raise

    async def _handle_message(self, message: Any) -> None:
        topic = getattr(message, "topic", "unknown")
        raw_value = message.value
        event_obj: Any = None

        try:
            if isinstance(raw_value, (bytes, bytearray)):
                event_obj = json.loads(raw_value.decode("utf-8"))
            elif raw_value is not None:
                event_obj = raw_value
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            logger.warning("EVENT_DESERIALIZATION_FAILED topic=%s error=%s", topic, exc)
            deadletter = {
                "event": {
                    "raw_message": raw_value.decode("utf-8", "replace") if isinstance(raw_value, (bytes, bytearray)) else raw_value,
                },
                "error": f"Unable to deserialize event: {exc}",
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.producer.publish_deadletter(deadletter, error="Unable to deserialize event")
            return

        if not isinstance(event_obj, dict):
            logger.warning("EVENT_FORMAT_INVALID topic=%s payload_type=%s", topic, type(event_obj).__name__)
            deadletter = build_deadletter_message({"raw_message": raw_value}, "Event payload is not a JSON object")
            await self.producer.publish_deadletter(deadletter, error="Event payload is not a JSON object")
            return

        event_id = str(event_obj.get("event_id", "unknown"))
        logger.info("EVENT_RECEIVED event_id=%s topic=%s", event_id, topic)

        # Create ONE session for the entire event lifecycle
        db = SessionLocal()
        try:
            # Step 1: Create event record with RECEIVED status
            try:
                self.event_repository.create_event(db, event_obj)
                db.commit()
            except Exception:
                db.rollback()
                existing_event = self.event_repository.get_by_event_id(db, event_id)
                if existing_event is not None and existing_event.status == EventStatus.PROCESSED.value:
                    logger.info("EVENT_ALREADY_PROCESSED event_id=%s", event_id)
                    return

            # Step 2: Validate event (does not touch database, no transaction impact)
            result = ValidationService.validate_event(event_obj)
            if not result.is_valid:
                logger.warning("EVENT_VALIDATION_FAILED event_id=%s topic=%s error=%s", event_id, topic, result.error)
                self.event_repository.update_status(
                    db,
                    event_id,
                    EventStatus.FAILED.value,
                    validation_error=result.error or "validation failed",
                )
                db.commit()
                deadletter = build_deadletter_message(event_obj, result.error or "validation failed")
                await self.producer.publish_deadletter(deadletter, error=result.error or "validation failed")
                return

            # Step 3: Mark event as VALIDATED
            self.event_repository.update_status(db, event_id, EventStatus.VALIDATED.value)
            db.commit()
            logger.info("EVENT_VALIDATED event_id=%s", event_id)

            # Step 4: Process the event and mark PROCESSED (or FAILED)
            # Pass the session to processor so it doesn't create its own
            try:
                self.event_processor.process(event_obj, db=db)
                # Process succeeded; event_repository already marked PROCESSED by processor
                # Explicit commit not needed; processor commits if it owns the session, but it doesn't (we pass db)
                # So we commit here to finalize the processing
                db.commit()
            except Exception as exc:
                # Processing failed; roll back and then mark FAILED in a new transaction
                db.rollback()
                logger.error("EVENT_PROCESSING_FAILED event_id=%s error=%s", event_id, exc)

                # Create a fresh session to mark event as FAILED (separate transaction)
                db_failed = SessionLocal()
                try:
                    self.event_repository.update_status(
                        db_failed,
                        event_id,
                        EventStatus.FAILED.value,
                        validation_error=str(exc),
                    )
                    db_failed.commit()
                except Exception as exc_failed:
                    db_failed.rollback()
                    logger.error("EVENT_STATUS_UPDATE_FAILED event_id=%s error=%s", event_id, exc_failed)
                finally:
                    db_failed.close()

                # Send to deadletter
                deadletter = build_deadletter_message(event_obj, str(exc))
                await self.producer.publish_deadletter(deadletter, error=str(exc))
        finally:
            db.close()

    async def consume_forever(self) -> None:
        await self.start()
        if self.consumer is None:
            raise RuntimeError("Kafka consumer could not be initialized")

        try:
            async for message in self.consumer:
                await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("KAFKA_CONSUMER_STOPPING group_id=%s", self.group_id)
            raise
        except Exception as exc:
            logger.exception("KAFKA_CONSUMER_ERROR group_id=%s error=%s", self.group_id, exc)
            raise

    async def stop(self) -> None:
        if self.consumer is not None:
            await self.consumer.stop()
            self.consumer = None
            logger.info("KAFKA_DISCONNECTED group_id=%s", self.group_id)
        await self.producer.close()


consumer = HealthcareKafkaConsumer()
