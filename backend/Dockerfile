FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    HF_HOME=/app/.hf_cache \
    TRANSFORMERS_CACHE=/app/.hf_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/.hf_cache \
    HF_HUB_READ_TIMEOUT=60 \
    HF_HUB_ETAG_TIMEOUT=60

WORKDIR /app

# System deps (psycopg2 / build essentials)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
 && python -m pip install --no-cache-dir --prefer-binary -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]

