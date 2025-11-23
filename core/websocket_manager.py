from fastapi import WebSocket
from typing import List, Dict, Any
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.device_connections: Dict[int, WebSocket] = {}  # 🔹 Dispositivos conectados

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Nueva conexión ({len(self.active_connections)} activas)")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"❌ Conexión cerrada ({len(self.active_connections)} restantes)")

    async def send_json(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"[Error al enviar mensaje WS] {e}")

    async def broadcast_json(self, message: Dict[str, Any]):
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print(f"[Error envío WS] {e}")
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def send_to_device(self, device_id: int, message: Dict[str, Any]):
        """Envia mensaje solo a un dispositivo específico"""
        ws = self.device_connections.get(device_id)
        if ws:
            try:
                await self.send_json(ws, message)
                print(f"✅ Mensaje enviado al dispositivo {device_id}")
            except Exception as e:
                print(f"❌ Error enviando al dispositivo {device_id}: {e}")
                self.device_connections.pop(device_id, None)
        else:
            print(f"⚠️ No hay conexión activa para el dispositivo {device_id}")

# Instancia global
manager = ConnectionManager()