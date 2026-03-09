FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Actualizar pip es clave para resolver errores de "No matching distribution"
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalamos los binarios del navegador
RUN playwright install chromium

COPY . .

CMD ["python", "amazon_bot.py"]
