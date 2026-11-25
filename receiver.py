import connexion
import json
import time
import logging
import logging.config
import yaml
import os
import asyncio

from aiokafka.errors import KafkaConnectionError, KafkaError
from contextlib import asynccontextmanager
from connexion import NoContent, request
from aiokafka import AIOKafkaProducer


KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "localhost:19092"
)

KAFKA_ATTENDANCE_TOPIC = os.getenv(
    "KAFKA_ATTENDANCE_TOPIC",
    "stadium-attendance"
)

KAFKA_TICKET_TOPIC = os.getenv(
    "KAFKA_TICKET_TOPIC",
    "ticket-sales"
)


with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f)

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("receiver")

async def start_producer():
    delay = 1

    while True:
        producer = AIOKafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            enable_idempotence=True,
            request_timeout_ms=10_000,
            retry_backoff_ms=250,
            linger_ms=5
        )

        try:
            await producer.start()
            logger.info("Kafka producer started.")
            return producer

        except KafkaConnectionError:
            logger.warning(
                "Kafka not reachable, retrying in %s seconds.",
                delay
            )

            await producer.stop()
            await asyncio.sleep(delay)

            delay = min(delay * 2, 30)

@asynccontextmanager
async def lifespan(app):
    producer = await start_producer()

    try:
        yield {"kafka": producer}

    finally:
        logger.info("Stopping Kafka producer.")
        await producer.stop()


def get_status():
    return {"status": "running"}, 200


async def record_attendance(body):
    trace_id = time.time_ns()

    data = {
        **body,
        "trace_id": trace_id
    }

    payload = json.dumps(data)

    logger.info(
        "Received attendance event - attendance: %s | trace_id: %s",
        body["attendance"],
        trace_id
    )

    try:
        await asyncio.wait_for(
            request.state.kafka.send_and_wait(
                KAFKA_ATTENDANCE_TOPIC,
                payload.encode("utf-8")
            ),
            timeout=5
        )

    except (KafkaError, asyncio.TimeoutError):
        logger.exception(
            "Kafka unavailable, rejecting attendance event"
        )

        return {
            "error": "temporarily unavailable"
        }, 503

    logger.info(
        "Attendance event sent to Kafka | trace_id: %s",
        trace_id
    )

    return NoContent, 201

async def record_ticket_sale(body):
    trace_id = time.time_ns()

    data = {
        **body,
        "trace_id": trace_id
    }

    payload = json.dumps(data)

    logger.info(
        "Received ticket sale event - tickets_sold: %s | trace_id: %s",
        body["tickets_sold"],
        trace_id
    )

    try:
        await asyncio.wait_for(
            request.state.kafka.send_and_wait(
                KAFKA_TICKET_TOPIC,
                payload.encode("utf-8")
            ),
            timeout=5
        )

    except (KafkaError, asyncio.TimeoutError):
        logger.exception(
            "Kafka unavailable, rejecting ticket sale event"
        )

        return {
            "error": "temporarily unavailable"
        }, 503

    logger.info(
        "Ticket sale event sent to Kafka | trace_id: %s",
        trace_id
    )

    return NoContent, 201

async def start_producer():
    delay = 1

    while True:
        producer = AIOKafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            enable_idempotence=True,
            request_timeout_ms=10_000,
            retry_backoff_ms=250,
            linger_ms=5
        )

        try:
            await producer.start()
            logger.info("Kafka producer started.")
            return producer

        except KafkaConnectionError:
            logger.warning(
                "Kafka not reachable, retrying in %s seconds.",
                delay
            )

            await producer.stop()
            await asyncio.sleep(delay)

            delay = min(delay * 2, 30)

app = connexion.AsyncApp(
    __name__,
    specification_dir="",
    lifespan=lifespan
)

app.add_api(
    "soccer.yaml",
    strict_validation=True,
    validate_responses=True
)