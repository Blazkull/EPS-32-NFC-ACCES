from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.device_connections: Dict[int, WebSocket] = {}  # 🔹 Dispositivos conectados por ID

    async def connect(self, websocket: WebSocket, device_id: int = None):
        await websocket.accept()
        if device_id is not None:
            self.device_connections[device_id] = websocket
            print(f"✅ Dispositivo {device_id} conectado ({len(self.device_connections)} dispositivos)")
        else:
            self.active_connections.append(websocket)
            print(f"✅ Cliente conectado ({len(self.active_connections)} clientes)")

    def disconnect(self, websocket: WebSocket, device_id: int = None):
        if device_id is not None and device_id in self.device_connections:
            if self.device_connections[device_id] == websocket:
                del self.device_connections[device_id]
                print(f"❌ Dispositivo {device_id} desconectado ({len(self.device_connections)} restantes)")
        else:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                print(f"❌ Cliente desconectado ({len(self.active_connections)} restantes)")

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
                print(f"✅ Mensaje enviado al dispositivo {device_id}: {message}")
            except Exception as e:
                print(f"❌ Error enviando al dispositivo {device_id}: {e}")
                self.device_connections.pop(device_id, None)
        else:
            print(f"⚠️ No hay conexión activa para el dispositivo {device_id}")

# Instancia global
manager = ConnectionManager()