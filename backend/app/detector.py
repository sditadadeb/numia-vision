"""
YOLO Detection Engine - Contador de Personas + Heatmap
Detección de personas usando Ultralytics YOLOv8 con generación de mapa de calor.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Any, Tuple, Optional
import base64
from .config import get_settings

settings = get_settings()


class HeatmapGenerator:
    """Generador de mapas de calor basado en detecciones"""
    
    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.accumulator = np.zeros((height, width), dtype=np.float32)
        self.reference_image = None
        self.total_detections = 0
        self.frames_processed = 0
    
    def set_reference_image(self, image: np.ndarray):
        """Establece la imagen de referencia y resetea el acumulador"""
        self.reference_image = image.copy()
        self.height, self.width = image.shape[:2]
        self.accumulator = np.zeros((self.height, self.width), dtype=np.float32)
        self.total_detections = 0
        self.frames_processed = 0
    
    def add_detections(self, persons: List[Dict]):
        """Agrega detecciones al acumulador de calor"""
        self.frames_processed += 1
        
        for person in persons:
            bbox = person["bbox"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            
            # Asegurar que está dentro de los límites
            x1 = max(0, min(x1, self.width - 1))
            x2 = max(0, min(x2, self.width - 1))
            y1 = max(0, min(y1, self.height - 1))
            y2 = max(0, min(y2, self.height - 1))
            
            if x2 > x1 and y2 > y1:
                # Crear un gradiente gaussiano para la zona de la persona
                # El centro de la persona tiene más peso
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Crear máscara gaussiana
                for y in range(y1, y2):
                    for x in range(x1, x2):
                        # Distancia al centro normalizada
                        dx = (x - center_x) / ((x2 - x1) / 2 + 1)
                        dy = (y - center_y) / ((y2 - y1) / 2 + 1)
                        # Peso gaussiano
                        weight = np.exp(-(dx*dx + dy*dy) / 2)
                        self.accumulator[y, x] += weight
                
                self.total_detections += 1
    
    def add_detections_fast(self, persons: List[Dict]):
        """Versión rápida: solo incrementa el área del bbox"""
        self.frames_processed += 1
        
        for person in persons:
            bbox = person["bbox"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            
            # Asegurar límites
            x1 = max(0, min(x1, self.width - 1))
            x2 = max(0, min(x2, self.width - 1))
            y1 = max(0, min(y1, self.height - 1))
            y2 = max(0, min(y2, self.height - 1))
            
            if x2 > x1 and y2 > y1:
                # Incrementar toda la zona (más rápido)
                self.accumulator[y1:y2, x1:x2] += 1
                self.total_detections += 1
    
    def generate_heatmap(self, alpha: float = 0.6) -> np.ndarray:
        """Genera el heatmap visual sobre la imagen de referencia"""
        if self.reference_image is None:
            # Si no hay imagen de referencia, crear fondo negro
            base = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        else:
            base = self.reference_image.copy()
        
        if self.accumulator.max() == 0:
            return base
        
        # Normalizar acumulador a 0-255
        normalized = (self.accumulator / self.accumulator.max() * 255).astype(np.uint8)
        
        # Aplicar blur para suavizar
        blurred = cv2.GaussianBlur(normalized, (25, 25), 0)
        
        # Aplicar colormap (JET: azul=frío, rojo=caliente)
        heatmap_colored = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)
        
        # Crear máscara donde hay datos
        mask = blurred > 10
        mask_3ch = np.stack([mask, mask, mask], axis=-1)
        
        # Combinar con imagen base
        result = base.copy()
        result[mask_3ch] = cv2.addWeighted(
            base, 1 - alpha, heatmap_colored, alpha, 0
        )[mask_3ch]
        
        return result
    
    def generate_heatmap_only(self) -> np.ndarray:
        """Genera solo el heatmap sin imagen de fondo"""
        if self.accumulator.max() == 0:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        normalized = (self.accumulator / self.accumulator.max() * 255).astype(np.uint8)
        blurred = cv2.GaussianBlur(normalized, (25, 25), 0)
        return cv2.applyColorMap(blurred, cv2.COLORMAP_JET)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del heatmap"""
        if self.accumulator.max() == 0:
            return {
                "total_detections": 0,
                "frames_processed": self.frames_processed,
                "hottest_zone": None,
                "coverage_percent": 0
            }
        
        # Encontrar zona más caliente
        max_idx = np.unravel_index(np.argmax(self.accumulator), self.accumulator.shape)
        hottest_y, hottest_x = max_idx
        
        # Calcular cobertura (% del área con detecciones)
        coverage = (self.accumulator > 0).sum() / (self.width * self.height) * 100
        
        return {
            "total_detections": self.total_detections,
            "frames_processed": self.frames_processed,
            "hottest_zone": {"x": int(hottest_x), "y": int(hottest_y)},
            "coverage_percent": round(coverage, 1),
            "max_intensity": float(self.accumulator.max())
        }
    
    def reset(self):
        """Resetea el acumulador"""
        self.accumulator = np.zeros((self.height, self.width), dtype=np.float32)
        self.total_detections = 0
        self.frames_processed = 0


class PersonDetector:
    def __init__(self):
        # Cargar modelo YOLO
        self.model = YOLO(settings.yolo_model)
        self.confidence_threshold = settings.confidence_threshold
        self.person_class_id = 0
        
        # Filtros de tamaño para evitar falsos positivos
        self.min_person_height = 100
        self.min_person_width = 40
        self.min_person_area = 8000
        self.person_confidence_threshold = 0.55
        
        # Generador de heatmap
        self.heatmap_generator = None
        
        print("[INFO] Detector YOLO inicializado")
    
    def init_heatmap(self, reference_image: np.ndarray = None, width: int = 640, height: int = 480):
        """Inicializa el generador de heatmap"""
        if reference_image is not None:
            h, w = reference_image.shape[:2]
            self.heatmap_generator = HeatmapGenerator(w, h)
            self.heatmap_generator.set_reference_image(reference_image)
        else:
            self.heatmap_generator = HeatmapGenerator(width, height)
        print(f"[INFO] Heatmap inicializado: {self.heatmap_generator.width}x{self.heatmap_generator.height}")
    
    def detect_people(self, frame: np.ndarray, update_heatmap: bool = False) -> Dict[str, Any]:
        """
        Detecta personas en el frame.
        
        Args:
            frame: Imagen en formato numpy array (BGR)
            update_heatmap: Si True, actualiza el heatmap con las detecciones
        
        Returns:
            Dict con count, persons y annotated_frame
        """
        results = self.model(frame, verbose=False)[0]
        
        persons = []
        
        for box in results.boxes:
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            if class_id != 0:
                continue
                
            if conf < self.person_confidence_threshold:
                continue
            
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            width = x2 - x1
            height = y2 - y1
            area = width * height
            
            if height < self.min_person_height or width < self.min_person_width or area < self.min_person_area:
                continue
            
            person = {
                "id": len(persons) + 1,
                "confidence": round(conf, 2),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "center": {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2}
            }
            persons.append(person)
        
        # Actualizar heatmap si está activo
        if update_heatmap and self.heatmap_generator:
            self.heatmap_generator.add_detections_fast(persons)
        
        # Dibujar en el frame
        annotated_frame = self._draw_detections(frame.copy(), persons)
        
        return {
            "count": len(persons),
            "persons": persons,
            "annotated_frame": annotated_frame
        }
    
    def get_heatmap(self, alpha: float = 0.6) -> Optional[np.ndarray]:
        """Obtiene el heatmap actual"""
        if self.heatmap_generator:
            return self.heatmap_generator.generate_heatmap(alpha)
        return None
    
    def get_heatmap_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del heatmap"""
        if self.heatmap_generator:
            return self.heatmap_generator.get_stats()
        return {}
    
    def reset_heatmap(self):
        """Resetea el heatmap"""
        if self.heatmap_generator:
            self.heatmap_generator.reset()
    
    def _draw_detections(self, frame: np.ndarray, persons: List[Dict]) -> np.ndarray:
        """Dibuja las detecciones en el frame"""
        
        COLOR_PERSON = (0, 200, 150)
        
        for person in persons:
            bbox = person["bbox"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            conf = person["confidence"]
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_PERSON, 2)
            
            corner_len = 15
            thickness = 3
            cv2.line(frame, (x1, y1), (x1 + corner_len, y1), COLOR_PERSON, thickness)
            cv2.line(frame, (x1, y1), (x1, y1 + corner_len), COLOR_PERSON, thickness)
            cv2.line(frame, (x2, y1), (x2 - corner_len, y1), COLOR_PERSON, thickness)
            cv2.line(frame, (x2, y1), (x2, y1 + corner_len), COLOR_PERSON, thickness)
            cv2.line(frame, (x1, y2), (x1 + corner_len, y2), COLOR_PERSON, thickness)
            cv2.line(frame, (x1, y2), (x1, y2 - corner_len), COLOR_PERSON, thickness)
            cv2.line(frame, (x2, y2), (x2 - corner_len, y2), COLOR_PERSON, thickness)
            cv2.line(frame, (x2, y2), (x2, y2 - corner_len), COLOR_PERSON, thickness)
            
            label = f"#{person['id']} ({int(conf*100)}%)"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - 22), (x1 + w + 8, y1), COLOR_PERSON, -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        self._draw_counter_panel(frame, len(persons))
        
        return frame
    
    def _draw_counter_panel(self, frame: np.ndarray, count: int):
        """Dibuja el panel con el contador de personas"""
        panel_h = 70
        cv2.rectangle(frame, (10, 10), (200, panel_h), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (200, panel_h), (0, 200, 150), 2)
        cv2.putText(frame, "NUMIA VISION", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 150), 2)
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
