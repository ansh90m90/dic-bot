# The Fool's Attendant — Fly.io container image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source.
COPY . .

# Writable state directory (a Fly volume is mounted here at /data).
RUN mkdir -p /data

CMD ["python", "main.py"]
