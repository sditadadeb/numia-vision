# Imagen Python con OpenCV
FROM python:3.11-slim-bookworm

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Dependencias del sistema para OpenCV
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements y instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descargar modelo YOLO (se cachea en el build)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Copiar código
COPY . .

# Puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
