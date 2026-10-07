# Soccer Stadium Event Receiver

This project simulates a soccer league platform that receives two types of events:

- Stadium attendance events
- Ticket sale events

The receiver service accepts incoming events and forwards them synchronously to the storage service. The receiver also generates a unique `trace_id` for each event before forwarding it.

## Architecture

```text
Client / JMeter
      |
      v
Receiver Service
Port 8080
      |
      | HTTP POST
      v
Storage Service
Port 8090
      |
      v
MySQL Database
Port 3306
```

## Event Types

### Stadium Attendance

Example:

```json
{
  "stadium_id": "STAD-1",
  "attendance": 25000,
  "capacity": 40000,
  "timestamp": "2026-10-07T19:30:00Z"
}
```

### Ticket Sale

Example:

```json
{
  "stadium_id": "STAD-1",
  "tickets_sold": 4,
  "ticket_price": 75,
  "timestamp": "2026-10-07T19:30:00Z"
}
```

The receiver generates a `trace_id` and adds it to the event before forwarding it to the storage service.

## Install Dependencies

The project uses `uv` for dependency management.

```powershell
uv sync
```

## Start MySQL

MySQL runs in a Docker container defined in `docker-compose.yml`.

Start the database:

```powershell
docker compose up -d
```

Check that it is running:

```powershell
docker compose ps
```

## Run the Storage Service

From the `storage` directory:

```powershell
uv run uvicorn storage:app --reload --port 8090
```

Storage Swagger UI:

http://127.0.0.1:8090/ui/

The storage service saves events to the MySQL database.

## Run the Receiver Service

From the main project directory:

```powershell
uv run uvicorn receiver:app --reload --port 8080
```

Receiver Swagger UI:

http://127.0.0.1:8080/ui/

Requests should normally be sent to the receiver on port `8080`. The receiver then forwards them to the storage service on port `8090`.

## Logging and Tracing

Each event received by the receiver is assigned a unique `trace_id`.

The same `trace_id` is:

1. Logged by the receiver
2. Forwarded to the storage service
3. Logged by the storage service
4. Stored in the MySQL database

Logging configuration is stored in:

```text
log_conf.yml
```

INFO messages are written to the console and `app.log`. DEBUG messages are displayed in the console.

## Run JMeter

JMeter 5.6.3 must be installed locally.

The JMeter test plan sends requests to the receiver service on port `8080`.

Example:

```powershell
.\run-test.ps1 200 5
```

This runs:

- 200 threads
- 5 loops per thread
- 2 HTTP requests per loop
- 1 attendance event and 1 ticket sale event per loop
- 2,000 total HTTP requests

Expected events:

```text
1,000 attendance events
1,000 ticket sale events
```

The thread and loop values are passed to JMeter as external properties and are read by the test plan using:

```text
${__P(threads,10)}
${__P(loops,1)}
```

## Service Ports

| Service | Port |
|---|---:|
| Receiver | 8080 |
| Storage | 8090 |
| MySQL | 3306 |

## Technology

- Python
- Connexion / OpenAPI 3
- Uvicorn
- SQLAlchemy
- MySQL
- PyMySQL
- Docker Compose
- JMeter
- PowerShell
- Python logging / PyYAML
