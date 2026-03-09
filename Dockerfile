# Usamos la imagen que ya tiene Python y los navegadores instalados
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Evitamos que Python genere archivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalamos las librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Ejecutamos el bot
CMD ["python", "amazon_bot.py"]
