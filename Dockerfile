FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Instalamos git para poder descargar la librería de captcha desde GitHub
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

CMD ["python", "amazon_bot.py"]
