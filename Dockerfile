# Usamos la imagen oficial de Playwright que ya trae Python y los navegadores
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el bot
CMD ["python", "amazon_bot.py"]
