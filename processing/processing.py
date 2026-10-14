import asyncio
import json
import logging
import logging.config
import os
import time

from contextlib import asynccontextmanager
from pathlib import Path

import connexion
import httpx
import yaml

from connexion import request


BASE_DIR = Path(__file__).resolve().parent

STATS_FILE = Path(
    os.getenv(
        "STATS_FILE",
        str(BASE_DIR / "statistics.json")
    )
)

STORAGE_URL = os.getenv(
    "STORAGE_URL",
    "http://127.0.0.1:8090"
)

POLL_INTERVAL = float(
    os.getenv("POLL_INTERVAL", "5")
)


with open(BASE_DIR / "log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f)

logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger("processing")


DEFAULT_STATS = {
    "total_attendance_events": 0,
    "total_ticket_sale_events": 0,
    "max_attendance": 0,
    "total_ticket_revenue": 0.0,
    "last_attendance_updated": None,
    "last_ticket_sale_updated": None
}


def load_stats():
    if not STATS_FILE.exists():
        return DEFAULT_STATS.copy()

    with STATS_FILE.open("r") as f:
        return json.load(f)


def save_stats(stats):
    temp_file = STATS_FILE.with_suffix(".tmp")

    with temp_file.open("w") as f:
        json.dump(stats, f, indent=2)

    temp_file.replace(STATS_FILE)


async def fetch_events(client, endpoint, after=None):
    params = {}

    if after:
        params["after"] = after

    response = await client.get(
        f"{STORAGE_URL}{endpoint}",
        params=params
    )

    response.raise_for_status()

    return response.json()


async def update_statistics(client, stats, lock):
    start_time = time.perf_counter()

    logger.info("Starting statistics update.")

    # Read our current cursors
    async with lock:
        attendance_after = stats["last_attendance_updated"]
        ticket_after = stats["last_ticket_sale_updated"]

    # Ask storage only for events we have not processed yet
    attendance_events = await fetch_events(
        client,
        "/stadiums/attendance",
        attendance_after
    )

    ticket_events = await fetch_events(
        client,
        "/stadiums/ticket-sales",
        ticket_after
    )

    logger.info(
        "Received %d attendance events and %d ticket sale events.",
        len(attendance_events),
        len(ticket_events)
    )

    async with lock:

        for event in attendance_events:
            stats["total_attendance_events"] += 1

            stats["max_attendance"] = max(
                stats["max_attendance"],
                event["attendance"]
            )

        if attendance_events:
            stats["last_attendance_updated"] = max(
                event["recorded_timestamp"]
                for event in attendance_events
            )

        for event in ticket_events:
            stats["total_ticket_sale_events"] += 1

            revenue = (
                event["tickets_sold"]
                * event["ticket_price"]
            )

            stats["total_ticket_revenue"] += revenue

        stats["total_ticket_revenue"] = round(
            stats["total_ticket_revenue"],
            2
        )

        if ticket_events:
            stats["last_ticket_sale_updated"] = max(
                event["recorded_timestamp"]
                for event in ticket_events
            )

        snapshot = stats.copy()

    # File I/O is synchronous, so don't block the event loop
    await asyncio.to_thread(
        save_stats,
        snapshot
    )

    elapsed = time.perf_counter() - start_time

    logger.info(
        "Statistics updated: %s",
        snapshot
    )

    logger.info(
        "Statistics update completed in %.3f seconds.",
        elapsed
    )


async def update_loop(client, stats, lock):
    while True:
        try:
            await update_statistics(
                client,
                stats,
                lock
            )

        except httpx.HTTPError:
            logger.exception(
                "Unable to retrieve events from storage."
            )

        except Exception:
            logger.exception(
                "Unexpected processing error."
            )

        await asyncio.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app):
    stats = await asyncio.to_thread(load_stats)

    lock = asyncio.Lock()

    async with httpx.AsyncClient(timeout=5.0) as client:

        task = asyncio.create_task(
            update_loop(
                client,
                stats,
                lock
            )
        )

        logger.info(
            "Background statistics processor started."
        )

        try:
            yield {
                "stats": stats,
                "lock": lock
            }

        finally:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            logger.info(
                "Background statistics processor stopped."
            )


async def get_stats():
    async with request.state.lock:
        return dict(request.state.stats), 200


def get_status():
    return {
        "status": "running"
    }, 200


app = connexion.AsyncApp(
    __name__,
    specification_dir="",
    lifespan=lifespan
)

app.add_api(
    "processing.yaml",
    strict_validation=True,
    validate_responses=True
)