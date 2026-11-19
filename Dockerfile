# Production Dockerfile for India National Pollution Transport & Dispersion Explorer
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system-level geospatial and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt .

# Install Python production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project source and data
COPY . .

# Expose standard Streamlit port
EXPOSE 8501

# Health check to ensure persistent availability
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Launch production Streamlit server
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
