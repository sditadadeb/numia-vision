from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database - SQLite por defecto para desarrollo, PostgreSQL para producción
    database_url: str = "sqlite:///./numia_vision.db"
    
    # YOLO - Usar 'n' (nano) para mejor rendimiento en Render
    yolo_model: str = "yolov8n.pt"
    confidence_threshold: float = 0.50
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    frontend_url: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()

