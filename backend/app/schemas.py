from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


class DetectionResult(BaseModel):
    count: int
    boxes: List[BoundingBox]
    confidence_avg: float
    timestamp: datetime


class DetectionCreate(BaseModel):
    person_count: int
    camera_id: str = "default"
    confidence_avg: float
    bounding_boxes: Optional[List[dict]] = None


class DetectionResponse(BaseModel):
    id: int
    timestamp: datetime
    person_count: int
    camera_id: str
    confidence_avg: float
    
    class Config:
        from_attributes = True


class HourlyStatsResponse(BaseModel):
    hour: datetime
    camera_id: str
    avg_count: float
    max_count: int
    min_count: int
    total_detections: int
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    timestamp: datetime
    camera_id: str
    alert_type: str
    message: str
    person_count: int
    threshold: int
    acknowledged: Optional[datetime]
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    current_count: int
    avg_today: float
    max_today: int
    total_detections_today: int
    alerts_pending: int


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float


class HeatmapData(BaseModel):
    hour: int
    day: int  # 0=Lun, 6=Dom
    avg_count: float



