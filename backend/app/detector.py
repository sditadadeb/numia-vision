"""
YOLO Detection Engine - Contador de Personas
Detección simple de personas usando Ultralytics YOLOv8.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Any, Tuple
import base64
from .config import get_settings

settings = get_settings()


class PersonDetector:
    def __init__(self):
        # Cargar modelo YOLO
        self.model = YOLO(settings.yolo_model)
        self.confidence_threshold = settings.confidence_threshold
        self.person_class_id = 0
        
        # Filtros de tamaño para evitar falsos positivos
        self.min_person_height = 100  # altura mínima en pixels
        self.min_person_width = 40    # ancho mínimo en pixels
        self.min_person_area = 8000   # área mínima
        self.person_confidence_threshold = 0.55
        
        print("[INFO] Detector YOLO inicializado")
    
    def detect_people(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detecta personas en el frame.
        
        Returns:
            Dict con count, persons y annotated_frame
        """
        results = self.model(frame, verbose=False)[0]
        
        persons = []
        
        for box in results.boxes:
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            # Solo personas (class_id = 0 en COCO)
            if class_id != 0:
                continue
                
            if conf < self.person_confidence_threshold:
                continue
            
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            width = x2 - x1
            height = y2 - y1
            area = width * height
            
            # Filtro de tamaño para evitar falsos positivos
            if height < self.min_person_height or width < self.min_person_width or area < self.min_person_area:
                continue
            
            person = {
                "id": len(persons) + 1,
                "confidence": round(conf, 2),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            }
            persons.append(person)
        
        # Dibujar en el frame
        annotated_frame = self._draw_detections(frame.copy(), persons)
        
        return {
            "count": len(persons),
            "persons": persons,
            "annotated_frame": annotated_frame
        }
    
    def _draw_detections(self, frame: np.ndarray, persons: List[Dict]) -> np.ndarray:
        """Dibuja las detecciones en el frame"""
        
        COLOR_PERSON = (0, 200, 150)  # Verde Numia (BGR)
        
        for person in persons:
            bbox = person["bbox"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            conf = person["confidence"]
            
            # Rectángulo principal
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_PERSON, 2)
            
            # Esquinas destacadas
            corner_len = 15
            thickness = 3
            # Top-left
            cv2.line(frame, (x1, y1), (x1 + corner_len, y1), COLOR_PERSON, thickness)
            cv2.line(frame, (x1, y1), (x1, y1 + corner_len), COLOR_PERSON, thickness)
            # Top-right
            cv2.line(frame, (x2, y1), (x2 - corner_len, y1), COLOR_PERSON, thickness)
            cv2.line(frame, (x2, y1), (x2, y1 + corner_len), COLOR_PERSON, thickness)
            # Bottom-left
            cv2.line(frame, (x1, y2), (x1 + corner_len, y2), COLOR_PERSON, thickness)
            cv2.line(frame, (x1, y2), (x1, y2 - corner_len), COLOR_PERSON, thickness)
            # Bottom-right
            cv2.line(frame, (x2, y2), (x2 - corner_len, y2), COLOR_PERSON, thickness)
            cv2.line(frame, (x2, y2), (x2, y2 - corner_len), COLOR_PERSON, thickness)
            
            # Label con ID y confianza
            label = f"#{person['id']} ({int(conf*100)}%)"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - 22), (x1 + w + 8, y1), COLOR_PERSON, -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Panel de conteo
        self._draw_counter_panel(frame, len(persons))
        
        return frame
    
    def _draw_counter_panel(self, frame: np.ndarray, count: int):
        """Dibuja el panel con el contador de personas"""
        # Panel de fondo
        panel_h = 70
        cv2.rectangle(frame, (10, 10), (200, panel_h), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (200, panel_h), (0, 200, 150), 2)
        
        # Título
        cv2.putText(frame, "NUMIA VISION", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 150), 2)
        
        # Contador
        cv2.putText(frame, f"Personas: {count}", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Convierte un frame a base64"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode('utf-8')
    
    def base64_to_frame(self, base64_str: str) -> np.ndarray:
        """Convierte base64 a frame numpy"""
        img_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


# Singleton
_detector = None

def get_detector() -> PersonDetector:
    global _detector
    if _detector is None:
        _detector = PersonDetector()
    return _detector
