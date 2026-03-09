# Usamos la versión exacta que pide el sistema
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Instalamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# Ejecutamos
CMD ["python", "amazon_bot.py"]
