# 🐳 Dockerfile for APPS_BOT & Hermes Agent Engine
FROM python:3.11-slim

# Metadata labels (Source: USER.md §1 + SOUL.md §1)
LABEL maintainer="Kafnun Asep Nurhuda Al-Hakim <pt.saudagar@gmail.com>"
LABEL project="APPS_BOT - Antigravity Assistant Production Manager (APM)"
LABEL organization="PT. Saudagar"
LABEL architecture="Multi-Channel Bot Ecosystem (Gmail x Telegram x WhatsApp)"
LABEL version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Copy dependency requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and documentation
COPY . /app

# Create necessary persistent runtime directories
RUN mkdir -p /app/logs /app/hermes/data

# Expose default service port (Uvicorn / FastAPI)
EXPOSE 8080

# Default entrypoint runs the master CLI orchestrator
CMD ["python", "apps_bot_manager.py", "run", "all"]
