import connexion
import requests
import time
import logging
import logging.config
import yaml
from connexion import NoContent

STORAGE_URL = "http://127.0.0.1:8090"

with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f)
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("receiver")

def record_attendance(body):
    try:
        trace_id = time.time_ns()
        body["trace_id"] = trace_id
        logger.info(
            "Received attendance event - attendance: %s | trace_id: %s",
            body["attendance"],
            trace_id
        )
        response = requests.post(
            f"{STORAGE_URL}/stadiums/attendance",
            json=body,
            timeout=5
        )
        logger.debug(
            "Response for attendance event (trace_id: %s) has status %s",
            trace_id,
            response.status_code
        )
    except requests.RequestException:
        return {"message": "Storage service unavailable"}, 503

    if response.status_code == 201:
        return NoContent, 201

    return {"message": "Storage service rejected event"}, response.status_code


def record_ticket_sale(body):
    try:
        trace_id = time.time_ns()
        body["trace_id"] = trace_id
        logger.info(
            "Received ticket sale event - tickets_sold: %s | trace_id: %s",
            body["tickets_sold"],
            trace_id
        )
        response = requests.post(
            f"{STORAGE_URL}/stadiums/ticket-sales",
            json=body,
            timeout=5
        )
        logger.debug(
            "Response for ticket sale event (trace_id: %s) has status %s",
            trace_id,
            response.status_code
        )
    except requests.RequestException:
        return {"message": "Storage service unavailable"}, 503

    if response.status_code == 201:
        return NoContent, 201

    return {"message": "Storage service rejected event"}, response.status_code


app = connexion.AsyncApp(__name__, specification_dir="")

app.add_api(
    "soccer.yaml",
    strict_validation=True,
    validate_responses=True
)