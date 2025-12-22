# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install pymupdf first (large package, needs longer timeout)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout=300 --retries=5 pymupdf && \
    pip install --no-cache-dir --timeout=100 --retries=5 -r requirements.txt

# Copy the entire application
COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Expose ports for all servers
EXPOSE 8000 8001 8002 8003 8005 8006

# Default command to run all servers and API
CMD ["./start.sh"]