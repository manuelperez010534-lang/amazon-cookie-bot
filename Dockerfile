FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Actualizamos pip por seguridad
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalamos solo Chromium para que sea rápido
RUN playwright install chromium

COPY . .

CMD ["python", "amazon_bot.py"]
