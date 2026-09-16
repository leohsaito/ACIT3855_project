# Soccer Stadium Event Receiver

## Run the API

uv run uvicorn receiver:app --reload --port 8080

Swagger UI:

http://127.0.0.1:8080/ui/

## Run JMeter

JMeter 5.6.3 must be installed locally.

Example:

.\run-test.ps1 200 5

This runs:
- 200 threads
- 5 loops
- 2 requests per loop
- 2,000 total HTTP requests