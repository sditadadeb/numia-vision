from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, and_, case, desc
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from . import models, schemas
from .config import get_settings

settings = get_settings()
IS_SQLITE = "sqlite" in settings.database_url


# ============ SESSIONS ============

def create_session(db: DBSession, camera_id: str = "default", name: str = None) -> models.Session:
    """Crea una nueva sesión de grabación"""
    session = models.Session(
        camera_id=camera_id,
        name=name or f"Sesión {datetime.now().strftime('%d/%m %H:%M')}",
        is_active=True,
        unique_objects=[],
        alerts_summary=[]
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_session(db: DBSession, camera_id: str = "default") -> Optional[models.Session]:
    """Obtiene la sesión activa actual"""
    return db.query(models.Session).filter(
        and_(
            models.Session.camera_id == camera_id,
            models.Session.is_active == True
        )
    ).first()


def end_session(db: DBSession, session_id: int, stats: Dict[str, Any] = None) -> Optional[models.Session]:
    """Finaliza una sesión y guarda estadísticas"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        return None
    
    session.is_active = False
    session.ended_at = datetime.now()
    
    if session.started_at:
        duration = (session.ended_at - session.started_at).total_seconds()
        session.duration_seconds = int(duration)
    
    if stats:
        session.total_frames = stats.get("total_frames", 0)
        session.avg_persons = stats.get("avg_persons", 0)
        session.max_persons = stats.get("max_persons", 0)
        session.total_objects_detected = stats.get("total_objects", 0)
        session.total_interactions = stats.get("total_interactions", 0)
        session.total_security_alerts = stats.get("total_alerts", 0)
        session.unique_objects = stats.get("unique_objects", [])
        session.alerts_summary = stats.get("alerts_summary", [])
    
    db.commit()
    db.refresh(session)
    return session


def get_sessions(db: DBSession, camera_id: str = "default", limit: int = 50) -> List[models.Session]:
    """Lista de sesiones ordenadas por fecha"""
    return db.query(models.Session).filter(
        models.Session.camera_id == camera_id
    ).order_by(desc(models.Session.started_at)).limit(limit).all()


def get_session_by_id(db: DBSession, session_id: int) -> Optional[models.Session]:
    """Obtiene una sesión por ID"""
    return db.query(models.Session).filter(models.Session.id == session_id).first()


def update_session_notes(db: DBSession, session_id: int, notes: str) -> Optional[models.Session]:
    """Actualiza notas de una sesión"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session:
        session.notes = notes
        db.commit()
        db.refresh(session)
    return session


def delete_session(db: DBSession, session_id: int) -> bool:
    """Elimina una sesión y sus eventos"""
    # Eliminar eventos
    db.query(models.SessionEvent).filter(models.SessionEvent.session_id == session_id).delete()
    # Eliminar sesión
    result = db.query(models.Session).filter(models.Session.id == session_id).delete()
    db.commit()
    return result > 0


# ============ SESSION EVENTS ============

def create_session_event(
    db: DBSession, 
    session_id: int, 
    event_type: str, 
    data: Dict[str, Any],
    snapshot_b64: str = None
) -> models.SessionEvent:
    """Crea un evento en la sesión"""
    event = models.SessionEvent(
        session_id=session_id,
        event_type=event_type,
        data=data,
        snapshot_b64=snapshot_b64
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_session_events(db: DBSession, session_id: int) -> List[models.SessionEvent]:
    """Obtiene todos los eventos de una sesión"""
    return db.query(models.SessionEvent).filter(
        models.SessionEvent.session_id == session_id
    ).order_by(models.SessionEvent.timestamp).all()


def create_detection(db: DBSession, detection: schemas.DetectionCreate) -> models.Detection:
    """Guarda una nueva detección"""
    db_detection = models.Detection(
        person_count=detection.person_count,
        camera_id=detection.camera_id,
        confidence_avg=detection.confidence_avg,
        bounding_boxes=detection.bounding_boxes
    )
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)
    return db_detection


def get_detections(
    db: DBSession, 
    camera_id: str = "default",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
) -> List[models.Detection]:
    """Obtiene detecciones con filtros"""
    query = db.query(models.Detection).filter(models.Detection.camera_id == camera_id)
    
    if start_time:
        query = query.filter(models.Detection.timestamp >= start_time)
    if end_time:
        query = query.filter(models.Detection.timestamp <= end_time)
    
    return query.order_by(models.Detection.timestamp.desc()).limit(limit).all()


def get_latest_detection(db: DBSession, camera_id: str = "default") -> Optional[models.Detection]:
    """Obtiene la última detección"""
    return db.query(models.Detection)\
        .filter(models.Detection.camera_id == camera_id)\
        .order_by(models.Detection.timestamp.desc())\
        .first()


def get_today_stats(db: DBSession, camera_id: str = "default") -> dict:
    """Estadísticas del día actual"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = db.query(
        func.avg(models.Detection.person_count).label('avg_count'),
        func.max(models.Detection.person_count).label('max_count'),
        func.min(models.Detection.person_count).label('min_count'),
        func.count(models.Detection.id).label('total')
    ).filter(
        and_(
            models.Detection.camera_id == camera_id,
            models.Detection.timestamp >= today_start
        )
    ).first()
    
    return {
        "avg_count": round(result.avg_count or 0, 1),
        "max_count": result.max_count or 0,
        "min_count": result.min_count or 0,
        "total_detections": result.total or 0
    }


def get_hourly_data(
    db: DBSession, 
    camera_id: str = "default",
    hours: int = 24
) -> List[dict]:
    """Datos agrupados por hora para gráficos"""
    start_time = datetime.now() - timedelta(hours=hours)
    
    if IS_SQLITE:
        # SQLite: usar strftime
        hour_expr = func.strftime('%Y-%m-%d %H:00:00', models.Detection.timestamp)
    else:
        # PostgreSQL: usar date_trunc
        hour_expr = func.date_trunc('hour', models.Detection.timestamp)
    
    results = db.query(
        hour_expr.label('hour'),
        func.avg(models.Detection.person_count).label('avg_count'),
        func.max(models.Detection.person_count).label('max_count')
    ).filter(
        and_(
            models.Detection.camera_id == camera_id,
            models.Detection.timestamp >= start_time
        )
    ).group_by(hour_expr).order_by('hour').all()
    
    return [
        {
            "hour": r.hour if isinstance(r.hour, str) else (r.hour.isoformat() if r.hour else None),
            "avg_count": round(r.avg_count, 1) if r.avg_count else 0,
            "max_count": r.max_count or 0
        }
        for r in results
    ]


def get_weekly_heatmap(db: DBSession, camera_id: str = "default") -> List[dict]:
    """Datos para heatmap semanal (día x hora)"""
    start_time = datetime.now() - timedelta(days=7)
    
    if IS_SQLITE:
        # SQLite: usar strftime (%w = día de semana, %H = hora)
        day_expr = func.cast(func.strftime('%w', models.Detection.timestamp), type_=None)
        hour_expr = func.cast(func.strftime('%H', models.Detection.timestamp), type_=None)
    else:
        # PostgreSQL: usar extract
        day_expr = func.extract('dow', models.Detection.timestamp)
        hour_expr = func.extract('hour', models.Detection.timestamp)
    
    results = db.query(
        day_expr.label('day'),
        hour_expr.label('hour'),
        func.avg(models.Detection.person_count).label('avg_count')
    ).filter(
        and_(
            models.Detection.camera_id == camera_id,
            models.Detection.timestamp >= start_time
        )
    ).group_by(day_expr, hour_expr).all()
    
    return [
        {
            "day": int(r.day) if r.day else 0,
            "hour": int(r.hour) if r.hour else 0,
            "avg_count": round(r.avg_count, 1) if r.avg_count else 0
        }
        for r in results
    ]


# ============ ALERTS ============

def create_alert(
    db: DBSession,
    camera_id: str,
    alert_type: str,
    message: str,
    person_count: int,
    threshold: int
) -> models.Alert:
    """Crea una nueva alerta"""
    alert = models.Alert(
        camera_id=camera_id,
        alert_type=alert_type,
        message=message,
        person_count=person_count,
        threshold=threshold
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_pending_alerts(db: DBSession, camera_id: str = "default") -> List[models.Alert]:
    """Alertas no reconocidas"""
    return db.query(models.Alert)\
        .filter(
            and_(
                models.Alert.camera_id == camera_id,
                models.Alert.acknowledged.is_(None)
            )
        ).order_by(models.Alert.timestamp.desc()).all()


def acknowledge_alert(db: DBSession, alert_id: int) -> Optional[models.Alert]:
    """Marca una alerta como reconocida"""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if alert:
        alert.acknowledged = datetime.now()
        db.commit()
        db.refresh(alert)
    return alert


def get_alerts_count(db: DBSession, camera_id: str = "default") -> int:
    """Cuenta alertas pendientes"""
    return db.query(models.Alert)\
        .filter(
            and_(
                models.Alert.camera_id == camera_id,
                models.Alert.acknowledged.is_(None)
            )
        ).count()

