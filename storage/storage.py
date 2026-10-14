import logging
import logging.config
import yaml
import connexion

from sqlalchemy import select, func
from connexion import NoContent
from datetime import datetime
from db import make_session, ENGINE
from models import Attendance, TicketSale, Base


with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f)

logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("storage")


def parse_timestamp(timestamp):
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

def get_status():
    session = make_session()

    try:
        attendance_count = session.scalar(
            select(func.count()).select_from(Attendance)
        )

        ticket_sale_count = session.scalar(
            select(func.count()).select_from(TicketSale)
        )

        return {
            "status": "running",
            "attendance_count": attendance_count,
            "ticket_sale_count": ticket_sale_count
        }, 200

    except Exception:
        logger.exception("Status check failed.")
        return {
            "status": "error"
        }, 500

    finally:
        session.close()

def reset_database():
    try:
        Base.metadata.drop_all(ENGINE)
        Base.metadata.create_all(ENGINE)

        logger.warning("Database reset completed.")

        return {
            "message": "Database reset successfully"
        }, 200

    except Exception:
        logger.exception("Database reset failed.")

        return {
            "message": "Database reset failed"
        }, 500

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
        logger.exception(
            "Failed to store attendance event | trace_id: %s",
            body.get("trace_id")
        )
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
        logger.exception(
            "Failed to store attendance event | trace_id: %s",
            body.get("trace_id")
        )
        raise

    finally:
        session.close()

    logger.debug(
        "Stored ticket sale event with trace_id: %s",
        body["trace_id"]
    )

    return NoContent, 201

def get_attendance_events(after=None):
    session = make_session()

    try:
        query = select(Attendance)

        if after:
            after_dt = parse_timestamp(after)
            query = query.where(
                Attendance.recorded_timestamp > after_dt
            )

        events = session.scalars(query).all()

        logger.debug(
            "Found %d attendance events after %s",
            len(events),
            after
        )

        return [event.to_json() for event in events], 200

    finally:
        session.close()
        
def get_ticket_sale_events(after=None):
    session = make_session()

    try:
        query = select(TicketSale)

        if after:
            after_dt = parse_timestamp(after)
            query = query.where(
                TicketSale.recorded_timestamp > after_dt
            )

        events = session.scalars(query).all()

        logger.debug(
            "Found %d ticket sale events after %s",
            len(events),
            after
        )

        return [event.to_json() for event in events], 200

    finally:
        session.close()

app = connexion.AsyncApp(
    __name__,
    specification_dir=""
)

app.add_api(
    "storage.yaml",
    strict_validation=True,
    validate_responses=True
)