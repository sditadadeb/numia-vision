from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime
import json

from .config import get_settings
from .detector import get_detector

settings = get_settings()
app = FastAPI(title="Numia Vision API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_count: int = 0
        self.history: List[dict] = []
        self.max_history = 100
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Cliente conectado. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Cliente desconectado. Total: {len(self.active_connections)}")
    
    def add_to_history(self, count: int, timestamp: str):
        self.history.append({"count": count, "timestamp": timestamp})
        if len(self.history) > self.max_history:
            self.history.pop(0)

manager = ConnectionManager()


@app.get("/")
def root():
    return {"message": "Numia Vision API", "status": "running"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/stats/current")
def get_current_stats():
    """Estadísticas actuales en memoria"""
    return {
        "current_count": manager.current_count,
        "history": manager.history[-50:],
        "connections": len(manager.active_connections)
    }


@app.websocket("/ws/detect")
async def websocket_detect(websocket: WebSocket):
    """WebSocket para detección de personas en tiempo real"""
    await manager.connect(websocket)
    detector = get_detector()
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                print("[WS] Error decodificando JSON")
                continue
            except Exception as e:
                print(f"[WS] Error recibiendo: {e}")
                break
            
            if message.get("type") == "frame":
                try:
                    frame_b64 = message.get("frame")
                    if not frame_b64:
                        continue
                    
                    frame = detector.base64_to_frame(frame_b64)
                    result = detector.detect_people(frame)
                    annotated_b64 = detector.frame_to_base64(result["annotated_frame"])
                    
                    manager.current_count = result["count"]
                    timestamp = datetime.now().isoformat()
                    manager.add_to_history(result["count"], timestamp)
                    
                    response = {
                        "type": "detection",
                        "count": result["count"],
                        "persons": result["persons"],
                        "frame": annotated_b64,
                        "timestamp": timestamp,
                        "history": manager.history[-30:]
                    }
                    
                    await websocket.send_json(response)
                    
                except Exception as e:
                    print(f"[WS] Error procesando frame: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print("[WS] Cliente desconectó normalmente")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Error WebSocket: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/heatmap")
async def websocket_heatmap(websocket: WebSocket):
    """WebSocket para modo heatmap en tiempo real"""
    await manager.connect(websocket)
    detector = get_detector()
    heatmap_active = False
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"[WS Heatmap] Error: {e}")
                break
            
            msg_type = message.get("type")
            
            # Iniciar heatmap con imagen de referencia
            if msg_type == "init_heatmap":
                try:
                    ref_image_b64 = message.get("reference_image")
                    if ref_image_b64:
                        ref_image = detector.base64_to_frame(ref_image_b64)
                        detector.init_heatmap(reference_image=ref_image)
                    else:
                        # Sin imagen de referencia, usar dimensiones del primer frame
                        width = message.get("width", 640)
                        height = message.get("height", 480)
                        detector.init_heatmap(width=width, height=height)
                    
                    heatmap_active = True
                    await websocket.send_json({
                        "type": "heatmap_initialized",
                        "status": "ok"
                    })
                    print("[WS Heatmap] Heatmap inicializado")
                except Exception as e:
                    print(f"[WS Heatmap] Error inicializando: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            # Procesar frame y actualizar heatmap
            elif msg_type == "frame" and heatmap_active:
                try:
                    frame_b64 = message.get("frame")
                    if not frame_b64:
                        continue
                    
                    frame = detector.base64_to_frame(frame_b64)
                    
                    # Si no hay imagen de referencia, usar el primer frame
                    if detector.heatmap_generator and detector.heatmap_generator.reference_image is None:
                        detector.heatmap_generator.set_reference_image(frame)
                    
                    # Detectar personas y actualizar heatmap
                    result = detector.detect_people(frame, update_heatmap=True)
                    
                    # Obtener heatmap actual
                    heatmap = detector.get_heatmap(alpha=0.6)
                    heatmap_b64 = detector.frame_to_base64(heatmap) if heatmap is not None else None
                    
                    # Obtener stats
                    stats = detector.get_heatmap_stats()
                    
                    # Frame anotado
                    annotated_b64 = detector.frame_to_base64(result["annotated_frame"])
                    
                    response = {
                        "type": "heatmap_update",
                        "count": result["count"],
                        "persons": result["persons"],
                        "frame": annotated_b64,
                        "heatmap": heatmap_b64,
                        "stats": stats,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await websocket.send_json(response)
                    
                except Exception as e:
                    print(f"[WS Heatmap] Error procesando: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Resetear heatmap
            elif msg_type == "reset_heatmap":
                detector.reset_heatmap()
                await websocket.send_json({
                    "type": "heatmap_reset",
                    "status": "ok"
                })
                print("[WS Heatmap] Heatmap reseteado")
            
            # Obtener heatmap final
            elif msg_type == "get_final_heatmap":
                try:
                    heatmap = detector.get_heatmap(alpha=0.7)
                    heatmap_b64 = detector.frame_to_base64(heatmap) if heatmap is not None else None
                    stats = detector.get_heatmap_stats()
                    
                    await websocket.send_json({
                        "type": "final_heatmap",
                        "heatmap": heatmap_b64,
                        "stats": stats
                    })
                except Exception as e:
                    print(f"[WS Heatmap] Error obteniendo final: {e}")
            
            # Detener heatmap
            elif msg_type == "stop_heatmap":
                heatmap_active = False
                # Obtener heatmap final antes de parar
                heatmap = detector.get_heatmap(alpha=0.7)
                heatmap_b64 = detector.frame_to_base64(heatmap) if heatmap is not None else None
                stats = detector.get_heatmap_stats()
                
                await websocket.send_json({
                    "type": "heatmap_stopped",
                    "heatmap": heatmap_b64,
                    "stats": stats
                })
                print("[WS Heatmap] Heatmap detenido")
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print("[WS Heatmap] Cliente desconectó")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS Heatmap] Error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
