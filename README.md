# ACIT 3855 Final Project Defense README

This is a practical defense guide for the Soccer Stadium Event Platform.

## 1. Fast defense sequence

If asked to "show your project", use this order:

```powershell
docker compose ps
```

1. Open Receiver Swagger: `http://localhost:8088/receiver/ui/`
2. Send one attendance event.
3. Open Redpanda Console: `http://localhost:8088/redpanda/`
4. Show the event in `stadium-attendance`.
5. Show receiver and storage-worker logs.
6. Show raw processing stats with `docker compose exec processing cat /data/statistics.json`.
7. Run JMeter: `./run-test.ps1 -Threads 5 -Loops 5`.
8. Open Grafana: `http://localhost:8088/grafana/` and verify the panels update.
9. Demonstrate resilience by stopping MySQL, then Redpanda, and explain recovery.
10. Explain the reverse proxy and monitoring architecture.

---

## 2. Architecture

```text
JMeter / Browser / Swagger
          |
          v
     Caddy :8088
          |
   -------------------------
   |          |            |
Receiver   Processing    Storage API
 :8080       :8100        :8090
   |
   v
Redpanda / Kafka
   |
   v
Storage Worker
   |
   v
 MySQL

Observability:
Docker logs -> Alloy -> Loki -> Grafana
Redpanda metrics -> Prometheus -> Grafana
MySQL -> Grafana
Processing /stats -> Grafana
```

Important separation:

- `receiver` accepts new events.
- `redpanda` is the Kafka broker.
- `storage-worker` consumes Kafka and writes to MySQL.
- `storage` is the read API used by processing.
- `processing` calculates aggregate statistics.
- `caddy` is the reverse proxy.
- `prometheus` collects Redpanda metrics.
- `alloy` collects Docker logs.
- `loki` stores logs.
- `grafana` visualizes metrics, DB values, processing stats, and logs.

---

## 3. Main URLs

Use the reverse-proxy URLs during the defense.

```text
Receiver Swagger:   http://localhost:8088/receiver/ui/
Receiver status:    http://localhost:8088/receiver/status
Processing Swagger: http://localhost:8088/processing/ui/
Processing status:  http://localhost:8088/processing/status
Processing stats:   http://localhost:8088/processing/stats
Storage Swagger:    http://localhost:8088/storage/ui/
Storage status:     http://localhost:8088/storage/status
Grafana:            http://localhost:8088/grafana/
Redpanda Console:   http://localhost:8088/redpanda/
Prometheus:         http://localhost:8088/prometheus/
Prometheus targets: http://localhost:8088/prometheus/targets
```

---

## 4. Event types

Attendance example:

```json
{
  "stadium_id": "STAD-1",
  "attendance": 30000,
  "capacity": 40000,
  "timestamp": "2026-11-25T12:00:00Z"
}
```

Ticket sale example:

```json
{
  "stadium_id": "STAD-1",
  "tickets_sold": 25,
  "ticket_price": 75.50,
  "timestamp": "2026-11-25T12:00:00Z"
}
```

The receiver adds `trace_id`. Storage adds `recorded_timestamp`.

### timestamp vs recorded_timestamp

- `timestamp`: when the original event happened.
- `recorded_timestamp`: when storage persisted the event.
- Processing uses `recorded_timestamp` as its incremental cursor so it only requests newer records.

---

## 5. Send one event with Swagger

Open:

```text
http://localhost:8088/receiver/ui/
```

Use `POST /stadiums/attendance` with:

```json
{
  "stadium_id": "STAD-1",
  "attendance": 30000,
  "capacity": 40000,
  "timestamp": "2026-11-25T12:00:00Z"
}
```

Expected when Kafka is available: `201 Created`.

Flow:

```text
Swagger -> Caddy -> Receiver -> Kafka -> Storage Worker -> MySQL -> Storage API -> Processing
```

---

## 6. JMeter command-line test

```powershell
.\run-test.ps1 -Threads 5 -Loops 5
```

There are two event requests per loop:

```text
5 threads x 5 loops = 25 attendance events
5 threads x 5 loops = 25 ticket sale events
Total HTTP requests = 50
```

Formula:

```text
events per type = threads x loops
total events = threads x loops x 2
```

Compare the values before and after the test. Comparing deltas is safer than comparing absolute totals if Kafka/MySQL were reset at different times.

---

## 7. JMeter GUI

Start:

```powershell
.\apache-jmeter-5.6.3\bin\jmeter.bat
```

Use the project `.jmx` file.

Reverse-proxy settings:

```text
Protocol: http
Server Name or IP: 127.0.0.1
Port: 8088
```

Paths:

```text
/receiver/stadiums/attendance
/receiver/stadiums/ticket-sales
```

Header Manager:

```text
Content-Type: application/json
```

Example random values:

```text
${__Random(5000,30000,)}
${__Random(30000,60000,)}
```

If asked to change the range, edit it directly. For example:

```text
${__Random(20000,40000,)}
```

means generate values between 20,000 and 40,000.

---

## 8. Docker commands

Check services:

```powershell
docker compose ps
```

Stop:

```powershell
docker compose stop storage-worker
```

Start:

```powershell
docker compose start storage-worker
```

Rebuild/recreate:

```powershell
docker compose up -d --build --force-recreate storage-worker
```

Receiver:

```powershell
docker compose up -d --build --force-recreate receiver
```

Processing:

```powershell
docker compose up -d --build --force-recreate processing
```

Difference:

- `stop/start` uses the existing image/container.
- `--build` rebuilds the image from the Dockerfile.
- `--force-recreate` creates a fresh container.

---

## 9. Docker logs

```powershell
docker compose logs receiver
docker compose logs --since 5m receiver
docker compose logs -f storage-worker
```

Filter trace IDs:

```powershell
docker compose logs --since 10m receiver |
    Select-String "trace_id"
```

Filter warnings/errors:

```powershell
docker compose logs --since 10m storage-worker |
    Select-String "ERROR|WARNING|unavailable|retry"
```

Useful service names:

```text
receiver
storage
storage-worker
processing
redpanda
prometheus
loki
alloy
grafana
caddy
```

---

## 10. Kafka / Redpanda

Topics:

```text
stadium-attendance
ticket-sales
```

Open Redpanda Console:

```text
http://localhost:8088/redpanda/
```

Important Kafka concepts:

- Topic: logical stream of messages.
- Partition: ordered sequence within a topic.
- Offset: position of a message in a partition.
- Consumer group: coordinates consumers and tracks progress.
- `storage-worker` manually commits offsets after successfully handling messages.

CLI:

```powershell
docker compose exec redpanda rpk topic list
```

Consume one attendance message:

```powershell
docker compose exec redpanda rpk topic consume stadium-attendance -n 1
```

---

## 11. Why manual Kafka commits matter

```text
Kafka message
    |
    v
Try database insert
    |
    +-- success --> commit Kafka offset
    |
    +-- DB unavailable --> do NOT commit
                           retry same message
```

This prevents event loss if the database is temporarily unavailable.

---

## 12. Why trace_id is unique

Possible failure:

```text
DB insert succeeds
    |
worker crashes before Kafka commit
    |
Kafka redelivers message
    |
same trace_id
    |
unique DB constraint prevents duplicate row
```

This makes storage effectively idempotent for repeated Kafka deliveries.

---

## 13. Fault tolerance: Kafka down

```powershell
docker compose stop redpanda
```

Expected behavior:

- Receiver cannot publish new events.
- It should not falsely report successful Kafka delivery.
- Existing MySQL data remains intact.
- Storage can still serve already-persisted records.
- Processing can still work with data already in storage.

The receiver uses `send_and_wait()` plus a timeout.

Restart:

```powershell
docker compose start redpanda
```

Producer and consumer clients reconnect.

---

## 14. Fault tolerance: MySQL down

```powershell
docker compose stop db
```

Expected:

```text
Receiver        OK
Kafka           OK
Storage Worker  retrying
MySQL           DOWN
Storage API     degraded
Processing      cannot get newly stored records
```

The receiver can still publish to Kafka. The worker does not commit the Kafka offset until the DB write succeeds.

Restart:

```powershell
docker compose start db
```

Expected recovery:

- worker reconnects
- queued events are written
- offsets are committed
- processing catches up

---

## 15. Fault tolerance: storage-worker down

```powershell
docker compose stop storage-worker
```

Expected:

```text
Receiver       OK
Kafka          stores messages
MySQL          still available
Storage API    still available
Processing     sees no newly persisted events
```

Restart:

```powershell
docker compose start storage-worker
```

The worker consumes queued events and catches up.

---

## 16. Fault tolerance: storage API down

```powershell
docker compose stop storage
```

Ingestion still works:

```text
Receiver -> Kafka -> Storage Worker -> MySQL
```

Processing cannot fetch new records until storage returns.

Restart:

```powershell
docker compose start storage
```

Processing resumes and catches up.

---

## 17. Fault tolerance: processing down

```powershell
docker compose stop processing
```

Receiver, Kafka, storage-worker, and MySQL continue working.

Restart:

```powershell
docker compose start processing
```

Processing loads its persisted state and continues from its saved cursors.

---

## 18. Raw processing statistics

The real runtime file is:

```text
/data/statistics.json
```

Show it:

```powershell
docker compose exec processing cat /data/statistics.json
```

Typical fields:

```json
{
  "total_attendance_events": 157,
  "total_ticket_sale_events": 156,
  "max_attendance": 32500,
  "total_ticket_revenue": 140539,
  "last_attendance_updated": "...",
  "last_ticket_sale_updated": "..."
}
```

The local `processing/statistics.json` is not necessarily the live Docker runtime state. The live file is `/data/statistics.json` in the processing volume.

---

## 19. Why statistics.json reappears if deleted

If `/data/statistics.json` is deleted while processing is still running, the running Python process still has the statistics in memory.

On the next save cycle:

```text
Python memory -> save_stats() -> /data/statistics.json recreated
```

The Docker volume is not restoring a hidden backup copy.

---

## 20. Processing persistence

`processing_data` preserves processing state across container recreation.

```powershell
docker volume ls
```

If the container is recreated but the volume remains, the JSON persists. If the volume itself is deleted, the saved file is gone.

---

## 21. Purge MySQL data

If `/reset` is enabled:

```powershell
docker compose exec storage curl -X POST http://localhost:8090/reset
```

Verify:

```powershell
docker compose exec db mysql `
  -u soccer_user `
  -psoccer_password `
  soccer_events `
  -e "SELECT COUNT(*) AS attendance FROM attendance; SELECT COUNT(*) AS ticket_sales FROM ticket_sale;"
```

---

## 22. Purge Kafka topics

```powershell
docker compose exec redpanda rpk topic list
```

Delete:

```powershell
docker compose exec redpanda rpk topic delete stadium-attendance
docker compose exec redpanda rpk topic delete ticket-sales
```

Recreate:

```powershell
docker compose exec redpanda rpk topic create stadium-attendance
docker compose exec redpanda rpk topic create ticket-sales
```

Kafka and MySQL are separate persistent stores. Resetting only one can make historical totals differ.

---

## 23. Purge processing state

First find the real volume name:

```powershell
docker volume ls
```

Then:

```powershell
docker compose stop processing
docker compose rm -f processing
docker volume rm <actual_processing_volume_name>
docker compose up -d processing
```

Do not hard-code the Compose project prefix; verify it with `docker volume ls`.

---

## 24. Clean reset concept

For a fully clean test, purge together:

```text
MySQL
Kafka topics
Processing volume
```

Otherwise absolute counts can differ. For load testing, compare increases from the baseline.

---

## 25. Grafana dashboard

Open:

```text
http://localhost:8088/grafana/
```

Important panels:

- Database Event Counts — MySQL row counts.
- Kafka Message Counts — Prometheus/Redpanda metrics.
- Processing Aggregate Stats — Infinity datasource reading processing `/stats`.
- Event Search / Trace — Loki logs.
- Failure and Recovery Logs — Loki filtered for operational errors.

---

## 26. Prometheus

Prometheus uses a pull model.

Your key target is:

```text
http://redpanda:9644/metrics
```

Open target health:

```text
http://localhost:8088/prometheus/targets
```

The Redpanda target should be `UP`.

Do not change the Redpanda scrape target to the public Caddy URL. Prometheus and Redpanda communicate directly through the Docker network.

---

## 27. Grafana Prometheus datasource

Because Prometheus is served under `/prometheus`, Grafana should use:

```text
http://prometheus:9090/prometheus
```

Do not use `http://localhost:8088/prometheus` from inside Grafana. Inside a container, `localhost` refers to that container itself.

---

## 28. Kafka Prometheus queries

Attendance:

```promql
sum(vectorized_cluster_partition_end_offset{topic="stadium-attendance"})
-
sum(vectorized_cluster_partition_start_offset{topic="stadium-attendance"})
```

Ticket sales:

```promql
sum(vectorized_cluster_partition_end_offset{topic="ticket-sales"})
-
sum(vectorized_cluster_partition_start_offset{topic="ticket-sales"})
```

These represent retained messages in the topics. They can differ from DB totals if persistent stores were reset separately.

---

## 29. Loki and Alloy

```text
Docker stdout/stderr -> Alloy -> Loki -> Grafana
```

Alloy discovers containers through:

```text
/var/run/docker.sock
```

Grafana accesses Loki internally at:

```text
http://loki:3100
```

Loki is intentionally not publicly exposed.

---

## 30. How to access Loki

Normal method:

```text
Grafana -> Explore -> Loki
```

Example LogQL:

```logql
{service="receiver"}
```

To prove Loki itself is available from the Docker network:

```powershell
docker compose exec caddy wget -qO- http://loki:3100/ready
```

Expected:

```text
ready
```

Why not expose Loki directly? Grafana is the intended query/visualization layer and keeping Loki internal reduces attack surface.

---

## 31. Event trace search

Find a trace ID:

```powershell
docker compose logs --since 5m receiver |
    Select-String "trace_id"
```

Paste the trace ID into the Grafana search variable. The same ID can appear in receiver and storage-worker logs, showing the event's path through the system.

---

## 32. Reverse proxy

Caddy is the single external entry point.

```text
http://localhost:8088
```

Routing:

```text
/receiver/*   -> receiver:8080
/storage/*    -> storage:8090
/processing/* -> processing:8100
/grafana/*    -> grafana:3000
/redpanda/*   -> redpanda-console:8080
/prometheus/* -> prometheus:9090
```

Internal-only services such as MySQL, Kafka broker, Loki, and Alloy do not need direct browser access.

### Why use a reverse proxy?

- one entry point
- fewer exposed ports
- simpler URLs
- centralized routing
- easier HTTPS later
- reduced attack surface
- hides internal service addresses

---

## 33. Caddy 404 vs 502

`404` usually means Caddy reached the backend but the requested application route does not exist.

Example: `/receiver/` may become `/` and receiver has no `/` route. Use `/receiver/ui/` or `/receiver/status`.

`502 Bad Gateway` means Caddy could not successfully reach the backend service.

Troubleshoot with:

```powershell
docker compose ps
docker compose logs --tail 100 <service>
```

---

## 34. Docker networking

Compose services communicate by service name:

```text
receiver -> redpanda:9092
storage-worker -> db:3306
processing -> storage:8090
grafana -> prometheus:9090
grafana -> loki:3100
caddy -> receiver:8080
```

Inside a container, `localhost` means that container itself.

---

## 35. Monitoring architecture

Prometheus:

```text
Redpanda metrics -> Prometheus
```

Logging:

```text
Docker logs -> Alloy -> Loki
```

Grafana datasources:

```text
MySQL       -> database counts
Prometheus  -> Kafka metrics
Infinity    -> processing /stats
Loki        -> logs
```

Grafana is a visualization/query layer; it does not collect all data itself.

---

## 36. Key explanations to know

### Why Kafka?
Kafka decouples event ingestion from database persistence and buffers events during downstream failures.

### Why separate storage-worker and storage API?

```text
storage-worker: Kafka -> DB writes
storage:        HTTP -> DB reads
```

A failure in the read API does not stop ingestion.

### Why manual commits?
To avoid losing an event if the DB write fails.

### Why unique trace IDs?
To prevent duplicate rows if Kafka redelivers a message.

### Why persistent volumes?
Containers are disposable. Volumes preserve MySQL, Kafka, processing state, and Grafana configuration.

### Why Prometheus?
Time-series operational metrics.

### Why Loki?
Log storage/query.

### Why Alloy?
Docker log discovery/forwarding.

### Why Grafana?
One dashboard across multiple datasources.

### Why Caddy?
One externally accessible entry point with centralized routing and a smaller attack surface.

---

## 37. Useful troubleshooting commands

```powershell
docker compose ps
docker compose logs --tail 100 receiver
docker compose logs --tail 100 processing
docker compose logs --tail 100 storage-worker
docker compose logs --tail 100 caddy
docker compose logs --tail 100 prometheus
docker compose logs --tail 100 loki
docker compose logs --tail 100 alloy
```

Test internal connectivity from Caddy:

```powershell
docker compose exec caddy wget -qO- http://receiver:8080/status
docker compose exec caddy wget -qO- http://processing:8100/status
docker compose exec caddy wget -qO- http://storage:8090/status
docker compose exec caddy wget -qO- http://loki:3100/ready
```

---

## 38. Before the defense

Check:

```powershell
docker compose ps
```

Verify all of these:

```text
Receiver Swagger
Processing Swagger
Storage Swagger
Redpanda Console
Grafana
Prometheus Targets
```

Run a small JMeter test and confirm:

```text
DB counts increase
Kafka messages increase
Processing values update
Logs appear in Grafana
```

Show raw processing stats:

```powershell
docker compose exec processing cat /data/statistics.json
```

Show topics:

```powershell
docker compose exec redpanda rpk topic list
```

Be ready to stop/start/rebuild:

```text
db
redpanda
storage-worker
storage
processing
receiver
```

---

## 39. Final mental model

Application flow:

```text
Client -> Caddy -> Receiver -> Kafka -> Storage Worker -> MySQL -> Storage API -> Processing
```

Monitoring flow:

```text
Redpanda -> Prometheus -> Grafana
Docker logs -> Alloy -> Loki -> Grafana
MySQL -> Grafana
Processing /stats -> Grafana
```

If you understand those two flows and can demonstrate them, you can explain most of the defense.