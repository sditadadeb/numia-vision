from sqlalchemy import Column, Integer, Float, DateTime, String, JSON, Boolean, Text
from sqlalchemy.sql import func
from .database import Base


class Session(Base):
    """Sesión de grabación/detección"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)  # Nombre opcional de la sesión
    camera_id = Column(String(50), default="default", index=True)
    
    # Tiempos
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Estado
    is_active = Column(Boolean, default=True)
    
    # Estadísticas agregadas (se calculan al cerrar)
    total_frames = Column(Integer, default=0)
    avg_persons = Column(Float, default=0)
    max_persons = Column(Integer, default=0)
    total_objects_detected = Column(Integer, default=0)
    total_interactions = Column(Integer, default=0)
    total_security_alerts = Column(Integer, default=0)
    
    # Objetos únicos detectados durante la sesión
    unique_objects = Column(JSON, default=list)  # ["celular", "mochila", ...]
    
    # Resumen de alertas
    alerts_summary = Column(JSON, default=list)  # [{type, count, first_seen}, ...]
    
    # Notas del usuario
    notes = Column(Text, nullable=True)


class SessionEvent(Base):
    """Eventos importantes durante una sesión"""
    __tablename__ = "session_events"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Tipo de evento
    event_type = Column(String(50))  # 'person_entered', 'person_left', 'object_detected', 
                                      # 'interaction', 'security_alert', 'threshold_exceeded'
    
    # Datos del evento
    data = Column(JSON)  # Detalles específicos del evento
    
    # Snapshot (miniatura del frame cuando ocurrió)
    snapshot_b64 = Column(Text, nullable=True)


class Detection(Base):
    """Registro de cada detección de personas"""
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=True, index=True)  # Agregado
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    person_count = Column(Integer, nullable=False)
    camera_id = Column(String(50), default="default", index=True)
    confidence_avg = Column(Float)
    bounding_boxes = Column(JSON)


class HourlyStats(Base):
    """Estadísticas agregadas por hora"""
    __tablename__ = "hourly_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    hour = Column(DateTime(timezone=True), index=True, unique=True)
    camera_id = Column(String(50), default="default", index=True)
    avg_count = Column(Float)
    max_count = Column(Integer)
    min_count = Column(Integer)
    total_detections = Column(Integer)


class Alert(Base):
    """Alertas cuando se supera un umbral"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=True, index=True)  # Agregado
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    camera_id = Column(String(50), default="default")
    alert_type = Column(String(50))
    message = Column(String(255))
    person_count = Column(Integer)
    threshold = Column(Integer)
    acknowledged = Column(DateTime(timezone=True), nullable=True)
