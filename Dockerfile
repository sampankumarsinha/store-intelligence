FROM python:3.11-slim

WORKDIR /app

# API only — detection/YOLO runs on the host (see README). Keeps image ~100MB vs 2GB+.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY app ./app
COPY data ./data
COPY scripts ./scripts

ENV DATABASE_PATH=/app/data/store.db
ENV POS_PATH=/app/data/pos_transactions.csv

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
