import logging
import logging.config
import yaml
import connexion

from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
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

        return [
            event.to_json()
            for event in events
        ], 200

    except OperationalError:
        logger.warning(
            "Database unavailable for attendance GET"
        )

        return {
            "error": "database temporarily unavailable"
        }, 503

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
    
    except OperationalError:
        logger.warning(
            "Database unavailable for attendance GET"
        )

        return {
            "error": "database temporarily unavailable"
        }, 503
    
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