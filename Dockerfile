FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    "connexion[uvicorn]" \
    "connexion[swagger-ui]" \
    requests \
    pyyaml

COPY receiver.py .
COPY soccer.yaml .
COPY log_conf.yml .

EXPOSE 8080

CMD ["uvicorn", "receiver:app", "--host", "0.0.0.0", "--port", "8080"]