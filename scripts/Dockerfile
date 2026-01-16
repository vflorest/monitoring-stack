FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
RUN pip install --no-cache-dir psycopg2-binary

# Copiar script
COPY load_generator.py .

# Comando por defecto
CMD ["python", "load_generator.py", "--mode", "light"]
