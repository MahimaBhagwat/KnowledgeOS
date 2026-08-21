# Multi-stage Dockerfile for KnowledgeOS backend
# Uses Python 3.12 slim image for a production-ready, small footprint build

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Upgrade pip and prepare to build wheels for deterministic caching
RUN pip install --upgrade pip setuptools wheel

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Build wheels for all dependencies into /wheels to speed up final image installs
RUN pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# Final runtime image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy pre-built wheels and requirements, install from wheels (no-index)
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-deps --no-index -f /wheels -r requirements.txt

# Copy application code
COPY app ./app

# Ensure the application package root is importable
ENV PYTHONPATH=/app

# Network port where the application listens
EXPOSE 8000

# Run as non-root is preferred in production, but keep default for portability
# Definitive uvicorn execution entrypoint for serving the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
