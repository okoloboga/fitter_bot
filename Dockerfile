FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (wget for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run bot
CMD ["python", "main.py"]
