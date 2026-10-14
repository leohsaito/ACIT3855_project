# Soccer Stadium Processing and Statistics Service

The processing service periodically polls storage for new events, updates cumulative statistics, persists the statistics, and serves them through a `/stats` API.

This project uses the **all-in-one processing design**: the background statistics updater and the statistics API run in the same service.

## Architecture

```text
                      Docker internal network
                              |
                              v
Storage :8090  <----  Processing :8100
                         |      |
                         |      +--> GET /stats
                         |
                         +--> background polling loop
                              every ~5 seconds
```

The processing API is exposed to the host on port `8100`. Storage remains internal.

## Statistics

The service maintains at least four required statistics:

```text
total_attendance_events
total_ticket_sale_events
max_attendance
total_ticket_revenue
```

It also stores separate cursors:

```text
last_attendance_updated
last_ticket_sale_updated
```

Example:

```json
{
  "total_attendance_events": 31,
  "total_ticket_sale_events": 25,
  "max_attendance": 32500,
  "total_ticket_revenue": 19340.0,
  "last_attendance_updated": "2026-10-14T06:21:30.332655",
  "last_ticket_sale_updated": "2026-10-14T06:21:30.338532"
}
```

## How Incremental Processing Works

Each processing cycle:

1. Reads the last processed timestamp for each event type.
2. Calls storage:
   ```text
   GET /stadiums/attendance?after=<last_attendance_updated>
   GET /stadiums/ticket-sales?after=<last_ticket_sale_updated>
   ```
3. Receives only new events.
4. Updates the cumulative statistics.
5. Advances each cursor to the newest `recorded_timestamp`.
6. Writes the updated statistics to persistent storage.
7. Waits for the configured polling interval and repeats.

This avoids rereading the complete storage database on every cycle.

## Asynchronous Design

The processing service uses:

- `connexion.AsyncApp`
- an asynchronous lifespan function
- `asyncio.create_task(...)` for the background updater
- `httpx.AsyncClient` for non-blocking HTTP requests
- `await asyncio.sleep(...)` between processing cycles

The shared HTTP client is created once and reused instead of creating a new client for every request.

Using synchronous `requests` directly inside an `async def` function would block the event loop, so the processing service uses `httpx.AsyncClient`.

Synchronous file I/O can be moved off the event loop with:

```python
await asyncio.to_thread(...)
```

## Lifespan and `request.state`

The processing service initializes shared resources during the ASGI lifespan.

The lifespan function can:

- create the shared `httpx.AsyncClient`
- start the background processing task
- initialize the statistics state/lock
- cleanly cancel the background task and close resources when the service stops

Shared application resources are made available through `request.state` rather than depending on uncontrolled global variables.

## Persistent Statistics

In Docker, the active statistics file is:

```text
/data/statistics.json
```

Docker Compose mounts a named volume:

```text
processing_data:/data
```

Therefore the local file:

```text
processing/statistics.json
```

is **not** the live runtime file while Docker is running.

Inspect the real file:

```powershell
docker compose exec processing cat /data/statistics.json
```

## Atomic JSON Writes

The all-in-one design can use JSON because one service owns both updating and serving the statistics.

The file is written atomically:

```text
write temporary file
        ↓
replace statistics.json
```

This prevents the API from reading a partially written JSON document.

## Configuration

Typical environment variables:

```text
STORAGE_URL=http://storage:8090
POLL_INTERVAL=5
STATS_FILE=/data/statistics.json
```

This keeps deployment-specific values outside the Python source code.

## Run with Docker Compose

From the project root:

```powershell
docker compose up -d --build
```

Check:

```powershell
docker compose ps
```

## Swagger UI

```text
http://127.0.0.1:8100/ui/
```

## API Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/stats` | Return current aggregate statistics |
| GET | `/status` | Processing service health check |

## Logging

Recent logs:

```powershell
docker compose logs --since 2m processing
```

Follow live:

```powershell
docker compose logs -f processing
```

The logs should show:

```text
Starting statistics update.
Received X attendance events and Y ticket sale events.
Statistics updated: {...}
Statistics update completed in 0.00X seconds.
```

The service should also log failures when storage cannot be reached or a GET request fails.

If file logging is enabled:

```powershell
docker compose exec processing sh -c "tail -n 100 /app/app.log"
```

## Reset Processing Statistics for Testing

Processing statistics are persistent in the Docker named volume.

To reset only the processing state:

```powershell
docker compose stop processing
docker compose rm -f processing
docker volume ls
docker volume rm apiarc_processing_data
docker compose up -d processing
```

If the Compose project name changes, use the processing volume name shown by `docker volume ls`.

Do **not** remove the MySQL volume unless you intentionally want to delete the database too.

## End-to-End Test

### 1. Check current statistics

Open:

```text
http://127.0.0.1:8100/stats
```

or use Swagger:

```text
http://127.0.0.1:8100/ui/
```

### 2. Run JMeter

```powershell
.\run-test.ps1 -Threads 5 -Loops 5
```

Expected new events:

```text
25 attendance events
25 ticket-sale events
```

### 3. Wait for the next processing cycle

The service normally polls every few seconds.

### 4. Check `/stats` again

Both cumulative counters should increase by 25.

### 5. Compare with MySQL

```powershell
docker compose exec db mysql `
  -u soccer_user `
  -psoccer_password `
  soccer_events `
  -e "SELECT COUNT(*) AS attendance_count FROM attendance; SELECT COUNT(*) AS ticket_sale_count FROM ticket_sale;"
```

### 6. Check the persistent statistics file

```powershell
docker compose exec processing cat /data/statistics.json
```

The counts in MySQL, `/stats`, and `/data/statistics.json` should be consistent for a clean test state.

## Project Defense Guide

### Best Live Demonstration

Open one terminal and follow the processing logs:

```powershell
docker compose logs -f processing
```

In another terminal run:

```powershell
.\run-test.ps1 -Threads 5 -Loops 5
```

The strongest evidence is a processing cycle that shows non-zero new events:

```text
Starting statistics update.
Received 25 attendance events and 25 ticket sale events.
Statistics updated: ...
Statistics update completed in ...
```

Then open `/stats` and show the updated values.

### Be Ready to Explain

**Why did you choose an all-in-one processing service?**  
The background updater and statistics API are tightly related and share the same small statistics dataset. Keeping them in one service avoids the complexity of sharing state between two separate processing containers.

**Why is JSON acceptable here?**  
Only one processing service owns the JSON data. The file is written atomically and the workload is small. A shared JSON file between separate services would be a weaker design.

**Why use a Docker volume?**  
The statistics survive container recreation/restarts and do not need to be recomputed from scratch every time.

**Why are there two `last_updated` values?**  
Attendance and ticket-sale streams may be received at different times. Separate cursors allow each stream to advance independently without missing events.

**Why use `httpx.AsyncClient`?**  
The processing loop is asynchronous. An async HTTP client allows the event loop to handle other work while waiting for storage.

**What does `await asyncio.sleep()` do differently from `time.sleep()`?**  
`await asyncio.sleep()` yields control back to the event loop. `time.sleep()` would block the event-loop thread.

**What is the lifespan function for?**  
It initializes long-lived resources and the background task when the application starts, then closes/cancels them cleanly when the application stops.

**Why use `request.state`?**  
It gives API handlers controlled access to resources initialized by the application lifespan.

**Why does processing query storage using `after`?**  
It processes only new events rather than repeatedly retrieving the complete history.

## Technology

- Python
- Connexion / OpenAPI 3
- Uvicorn
- `asyncio`
- `httpx`
- Docker Compose
- Docker named volumes
- Atomic JSON persistence
- Python logging / PyYAML
