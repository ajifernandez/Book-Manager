# Utiliza una imagen base de Python
FROM python:3.12-slim

# Establece el directorio de trabajo
WORKDIR /app
# Instala las dependencias necesarias del sistema
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libzbar0 \
    && apt-get clean

# Copia el archivo de requisitos
COPY requirements.txt requirements.txt

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY . .

# Expone el puerto en el que correrá la aplicación
EXPOSE 5000

# Comando para correr la aplicación
CMD ["python", "run.py"]
