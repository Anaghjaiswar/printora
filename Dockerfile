# --- STAGE 1: BUILDER ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install python dependencies to a temporary directory
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- STAGE 2: FINAL ---
FROM python:3.11-slim AS final

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libgobject-2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi8 \
    shared-mime-info \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Security: Don't run as root
RUN useradd -m printora_user
RUN mkdir -p /app/staticfiles /app/media && chown -R printora_user:printora_user /app
USER printora_user

# Copy project code
COPY --chown=printora_user:printora_user . .

EXPOSE 8000

# Serve the project with ASGI via Gunicorn and Uvicorn workers.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-120}"]