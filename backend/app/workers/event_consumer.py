from __future__ import annotations

import asyncio

from app.kafka.consumer import HealthcareKafkaConsumer
from app.utils.logger import logger


async def run_consumer() -> None:
    consumer = HealthcareKafkaConsumer()
    try:
        await consumer.start()
        await consumer.consume_forever()
    except KeyboardInterrupt:
        logger.info("EVENT_CONSUMER_STOP_REQUESTED")
    except asyncio.CancelledError:
        logger.info("EVENT_CONSUMER_CANCELLED")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_consumer())
