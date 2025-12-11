FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (wget for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем curl для healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Копируем код приложения
COPY . .

# Run bot
CMD ["python", "main.py"]
