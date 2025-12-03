# Numia Vision 👁️

Sistema de **contador de personas en tiempo real** usando **YOLOv8 (Ultralytics)** con estadísticas y gráficos.

![YOLO](https://img.shields.io/badge/YOLO-v8-00FFFF?style=for-the-badge)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge)

## 🎯 Features

- 📹 **Vista en vivo** - Stream de cámara con detección en tiempo real
- 👥 **Contador de personas** - Detección precisa usando YOLOv8
- 📈 **Gráfico en tiempo real** - Visualización de la evolución del conteo
- 🚶 **Eventos entrada/salida** - Registro de cambios en la cantidad de personas
- 📊 **Estadísticas** - Máximo, promedio, total entradas/salidas
- 📁 **Historial** - Sesiones guardadas con gráficos y resumen
- 🌙 **Dark Theme** - Diseño moderno

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Recharts)                         │
│  • Vista cámara con WebSocket                               │
│  • Gráficos en tiempo real                                  │
│  • Panel de eventos y estadísticas                          │
│  • Historial de sesiones                                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket + REST API
┌─────────────────────▼───────────────────────────────────────┐
│  Backend (FastAPI + Python)                                 │
│  • YOLOv8 para detección de personas                        │
│  • WebSocket streaming                                      │
│  • APIs de estadísticas                                     │
│  • SQLite para persistencia                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Requisitos

- **Python 3.11+**
- **Node.js 18+**

---

### 📦 Backend

```bash
# Entrar al directorio
cd numia-vision/backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará en: **http://localhost:8000**

---

### 🎨 Frontend

```bash
# Entrar al directorio
cd numia-vision/frontend

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev
```

El frontend estará en: **http://localhost:5173**

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Info del API |
| GET | `/api/health` | Health check |
| GET | `/api/stats/current` | Estadísticas actuales en memoria |
| GET | `/api/stats/dashboard` | Estadísticas del dashboard |
| GET | `/api/stats/hourly` | Datos por hora |
| GET | `/api/sessions` | Lista de sesiones |
| GET | `/api/sessions/{id}` | Detalle de sesión |
| DELETE | `/api/sessions/{id}` | Eliminar sesión |
| WS | `/ws/detect` | WebSocket para detección |

---

## ⚙️ Configuración

Variables de entorno (`.env`):

| Variable | Descripción | Default |
|----------|-------------|---------|
| `YOLO_MODEL` | Modelo YOLO a usar | `yolov8s.pt` |
| `CONFIDENCE_THRESHOLD` | Umbral de confianza | `0.4` |
| `HOST` | Host del servidor | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8000` |

### Modelos YOLO disponibles

| Modelo | Tamaño | Velocidad | Precisión |
|--------|--------|-----------|-----------|
| `yolov8n.pt` | 6MB | ⚡⚡⚡ | ⭐⭐ |
| `yolov8s.pt` | 22MB | ⚡⚡ | ⭐⭐⭐ |
| `yolov8m.pt` | 52MB | ⚡ | ⭐⭐⭐⭐ |

---

## 🐳 Docker

```bash
docker-compose up --build
```

---

## 📄 Licencia

Este proyecto usa Ultralytics YOLO bajo licencia **AGPL-3.0**.

---

Desarrollado con 💚 por Numia
