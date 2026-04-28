# Usamos una imagen oficial de Python ligera
FROM python:3.12-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el archivo de dependencias y las instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo nuestro código y datos al contenedor
COPY . .

# Comando por defecto al iniciar el contenedor (por ahora ejecutará nuestro test)
CMD ["uvicorn", "generador_respuestas:app", "--host", "0.0.0.0", "--port", "8000"]