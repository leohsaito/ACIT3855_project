import json
import logging
import logging.config
import os
import signal
import yaml
import time

from datetime import datetime
from confluent_kafka import Consumer, KafkaException

from db import make_session
from models import Attendance, TicketSale
from sqlalchemy.exc import IntegrityError, OperationalError

KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "redpanda:9092"
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
logger = logging.getLogger("storage_worker")


def parse_timestamp(timestamp):
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def save_attendance(data):
    session = make_session()

    try:
        event = Attendance(
            trace_id=data["trace_id"],
            stadium_id=data["stadium_id"],
            attendance=data["attendance"],
            capacity=data["capacity"],
            timestamp=parse_timestamp(data["timestamp"])
        )

        try:
            session.add(event)
            session.commit()

        except IntegrityError:
            session.rollback()

            logger.info(
                "Duplicate attendance trace_id %s, already stored",
                data["trace_id"]
            )

        logger.info(
            "Stored attendance event | trace_id: %s",
            data["trace_id"]
        )

    except Exception:
        session.rollback()
        logger.exception(
            "Failed to store attendance event | trace_id: %s",
            data.get("trace_id")
        )
        raise

    finally:
        session.close()


def save_ticket_sale(data):
    session = make_session()

    try:
        event = TicketSale(
            trace_id=data["trace_id"],
            stadium_id=data["stadium_id"],
            tickets_sold=data["tickets_sold"],
            ticket_price=data["ticket_price"],
            timestamp=parse_timestamp(data["timestamp"])
        )

        try:
            session.add(event)
            session.commit()

        except IntegrityError:
            session.rollback()

            logger.info(
                "Duplicate ticket trace_id %s, already stored",
                data["trace_id"]
            )

        logger.info(
            "Stored ticket sale event | trace_id: %s",
            data["trace_id"]
        )

    except Exception:
        session.rollback()
        logger.exception(
            "Failed to store ticket sale event | trace_id: %s",
            data.get("trace_id")
        )
        raise

    finally:
        session.close()


def handle_sigterm(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, handle_sigterm)

def save_with_retry(save_function, data, max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        try:
            save_function(data)
            return True

        except OperationalError:
            logger.warning(
                "Database unavailable, attempt %d/%d",
                attempt,
                max_attempts
            )

            delay = min(2 ** attempt, 30)

            logger.info(
                "Retrying database operation in %d seconds.",
                delay
            )

            time.sleep(delay)

    return False

def main():
    config = {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": "storage_worker_group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False
    }

    consumer = Consumer(config)

    consumer.subscribe([
        KAFKA_ATTENDANCE_TOPIC,
        KAFKA_TICKET_TOPIC
    ])

    logger.info("Storage worker started.")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().fatal():
                    raise KafkaException(msg.error())

                logger.warning(
                    "Kafka error: %s",
                    msg.error()
                )
                continue

            try:
                data = json.loads(
                    msg.value().decode("utf-8")
                )

            except (ValueError, UnicodeDecodeError):
                logger.error(
                    "Malformed Kafka message at offset %s",
                    msg.offset()
                )

                consumer.commit(
                    msg,
                    asynchronous=False
                )

                continue


            if msg.topic() == KAFKA_ATTENDANCE_TOPIC:
                save_function = save_attendance

            elif msg.topic() == KAFKA_TICKET_TOPIC:
                save_function = save_ticket_sale

            else:
                logger.warning(
                    "Unknown Kafka topic: %s",
                    msg.topic()
                )

                consumer.commit(
                    msg,
                    asynchronous=False
                )

                continue


            saved = False

            while not saved:
                saved = save_with_retry(
                    save_function,
                    data
                )

                if not saved:
                    logger.warning(
                        "Database still unavailable. "
                        "Retrying same Kafka message in 5 seconds."
                    )

                    time.sleep(5)


            consumer.commit(
                msg,
                asynchronous=False
            )

            logger.debug(
                "Committed Kafka offset %s for topic %s",
                msg.offset(),
                msg.topic()
            )

    except KafkaException:
        logger.exception("Kafka failure.")

    except KeyboardInterrupt:
        logger.info("Storage worker stopping.")

    finally:
        logger.info("Closing Kafka consumer.")
        consumer.close()

if __name__ == "__main__":
    main()