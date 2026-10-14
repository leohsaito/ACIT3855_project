FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    "connexion[uvicorn]" \
    "connexion[swagger-ui]" \
    sqlalchemy \
    pymysql \
    pyyaml

COPY storage.py .
COPY storage.yaml .
COPY db.py .
COPY models.py .
COPY create_tables.py .
COPY drop_tables.py .
COPY log_conf.yml .

EXPOSE 8090

CMD ["sh", "-c", "python create_tables.py && uvicorn storage:app --host 0.0.0.0 --port 8090"]