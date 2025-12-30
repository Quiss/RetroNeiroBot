FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy alembic configuration and migrations
COPY alembic.ini .
COPY migrations/ ./migrations/
COPY bot/models/ ./bot/models/
COPY bot/__init__.py ./bot/__init__.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command (will be overridden in docker-compose)
CMD ["alembic", "upgrade", "head"]
