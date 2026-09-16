import connexion
import json
from pathlib import Path
from connexion import NoContent

EVENTS_FILE = Path(__file__).parent / "events.json"

def load_events():
    with open(EVENTS_FILE, "r") as file:
        return json.load(file)

def save_events(data):
    with open(EVENTS_FILE, "w") as file:
        json.dump(data, file, indent=4)

def record_attendance(body):
    print("Received attendance event:", body)
    data = load_events()
    data["attendance_events"].append(body)
    data["num_attendance_events"] += 1
    save_events(data)
    return NoContent, 201

def record_ticket_sale(body):
    print("Received ticket sale event:", body)
    data = load_events()
    data["ticket_sales_events"].append(body)
    data["num_ticket_sales_events"] += 1
    save_events(data)
    return NoContent, 201

app = connexion.AsyncApp(__name__, specification_dir="")

app.add_api(
    "soccer.yaml",
    strict_validation=True,
    validate_responses=True
)