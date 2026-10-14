# Soccer Stadium Event Receiver

The receiver is the public entry point for the soccer stadium event platform. It accepts attendance and ticket-sale events, generates a `trace_id`, logs the event, and forwards it to the internal storage service.

## Architecture

```text
JMeter / Client
      |
      | localhost:8080
      v
Receiver
      |
      | http://storage:8090
      v
Storage
      |
      | MySQL / SQLAlchemy
      v
Database

Processing
      |
      | polls http://storage:8090
      v
Storage
```

Only the **receiver** and **processing API** are exposed outside Docker. Storage and MySQL communicate only on the Docker Compose internal network.

## Event Types

### Stadium Attendance

```json
{
  "stadium_id": "STAD-1",
  "attendance": 32500,
  "capacity": 40000,
  "timestamp": "2026-09-15T19:30:00Z"
}
```

### Ticket Sale

```json
{
  "stadium_id": "STAD-1",
  "tickets_sold": 4,
  "ticket_price": 75.0,
  "timestamp": "2026-09-15T19:30:00Z"
}
```

The receiver adds a generated `trace_id` before forwarding the event to storage.

## Configuration

The storage URL is read from the `STORAGE_URL` environment variable.

Local default:

```text
http://127.0.0.1:8090
```

Docker Compose value:

```text
http://storage:8090
```

Inside Docker, service names such as `storage` act as DNS hostnames. `localhost` inside the receiver container would refer to the receiver container itself, not storage.

## Run with Docker Compose

From the project root:

```powershell
docker compose up -d --build
```

Check container status:

```powershell
docker compose ps
```

Do **not** start another local Uvicorn receiver on port `8080` while Docker is running. An old local Python/Uvicorn process can intercept requests intended for Docker.

To check whether port 8080 is already in use:

```powershell
netstat -ano | findstr :8080
```

## Swagger UI

```text
http://127.0.0.1:8080/ui/
```

## API Routes

| Method | Route | Purpose |
|---|---|---|
| POST | `/stadiums/attendance` | Receive an attendance event |
| POST | `/stadiums/ticket-sales` | Receive a ticket-sale event |
| GET | `/status` | Receiver health check |

Successful event POST requests should return `201 Created`.

## Logging and Tracing

Each incoming event receives a `trace_id`. The same ID can be followed through the receiver log, storage log, and MySQL record.

Useful commands:

```powershell
docker compose logs --since 2m receiver
docker compose logs -f receiver
```

If file logging is enabled:

```powershell
docker compose exec receiver sh -c "tail -n 100 /app/app.log"
```

## JMeter Load Test

Example:

```powershell
.\run-test.ps1 -Threads 5 -Loops 5
```

Expected result:

```text
5 threads x 5 loops = 25 attendance events
5 threads x 5 loops = 25 ticket-sale events
50 total HTTP requests
```

The test plan uses:

```text
${__P(threads,10)}
${__P(loops,1)}
```

## Project Defense Guide

### What to Demonstrate

1. Show the Docker stack with `docker compose ps`.
2. Open `http://127.0.0.1:8080/ui/`.
3. Send one event and show `201 Created`.
4. Run `./run-test.ps1 -Threads 5 -Loops 5`.
5. Show that storage/MySQL row counts increase and processing later includes the events.
6. Show a `trace_id` in the receiver log and explain that it is forwarded unchanged to storage.

### Be Ready to Explain

**Why is the receiver exposed but storage is not?**  
The receiver is the public entry point. Storage is an internal microservice and does not need a host port.

**Why use `STORAGE_URL` instead of hard-coding the address?**  
External configuration lets the same code run locally and in Docker without source changes.

**Why does Docker use `storage:8090` instead of `127.0.0.1:8090`?**  
Each container has its own network namespace. Docker Compose provides DNS using service names.

**Why use a `trace_id`?**  
It lets one event be followed across services for debugging and observability.

**The receiver uses `requests`. Is that a problem with `AsyncApp`?**  
The receiver handlers are synchronous functions. The important mistake to avoid is putting blocking `requests` calls directly inside an `async def` handler, where they would block the event loop.

## Useful Commands

```powershell
# Start or rebuild everything
docker compose up -d --build

# Show status
docker compose ps

# Receiver logs
docker compose logs --since 2m receiver

# Check receiver health
curl.exe http://127.0.0.1:8080/status
```

## Technology

- Python
- Connexion / OpenAPI 3
- Uvicorn
- `requests`
- Docker Compose
- JMeter
- Python logging / PyYAML
