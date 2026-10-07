import logging
import logging.config
import yaml
import connexion

from connexion import NoContent
from datetime import datetime
from db import make_session
from models import Attendance, TicketSale


with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f)

logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("storage")


def parse_timestamp(timestamp):
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def store_attendance(body):
    session = make_session()

    try:
        event = Attendance(
            trace_id=body["trace_id"],
            stadium_id=body["stadium_id"],
            attendance=body["attendance"],
            capacity=body["capacity"],
            timestamp=parse_timestamp(body["timestamp"])
        )

        session.add(event)
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()

    logger.debug(
        "Stored attendance event with trace_id: %s",
        body["trace_id"]
    )

    return NoContent, 201


def store_ticket_sale(body):
    session = make_session()

    try:
        event = TicketSale(
            trace_id=body["trace_id"],
            stadium_id=body["stadium_id"],
            tickets_sold=body["tickets_sold"],
            ticket_price=body["ticket_price"],
            timestamp=parse_timestamp(body["timestamp"])
        )

        session.add(event)
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()

    logger.debug(
        "Stored ticket sale event with trace_id: %s",
        body["trace_id"]
    )

    return NoContent, 201


app = connexion.AsyncApp(
    __name__,
    specification_dir=""
)

app.add_api(
    "storage.yaml",
    strict_validation=True,
    validate_responses=True
)