# ----------------------------
# Base image
# ----------------------------
FROM python:3.11-slim-bullseye

# ----------------------------
# Metadata
# ----------------------------
LABEL maintainer="mispartechnologies.com"
LABEL description="Smart Attendance System API"

# ----------------------------
# Set environment variables
# ----------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# ----------------------------
# Install system dependencies
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Set working directory
# ----------------------------
WORKDIR /app

# ----------------------------
# Copy only requirements first for caching
# ----------------------------
COPY requirements.txt .

# Upgrade pip/setuptools/wheel and install dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ----------------------------
# Copy the rest of the app
# ----------------------------
COPY . .

# ----------------------------
# Expose port
# ----------------------------
EXPOSE 8000

# ----------------------------
# Default command
# ----------------------------
CMD ["gunicorn", "smartattendancesystemapi.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]

