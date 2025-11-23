from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket_manager import manager
import json

router = APIRouter()

@router.websocket("/ws/device/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    await manager.connect(websocket)
    
    # Registrar el dispositivo
    manager.device_connections[device_id] = websocket
    print(f"✅ Dispositivo {device_id} conectado vía WebSocket")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"📩 Mensaje recibido del dispositivo {device_id}: {data}")
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Manejar autenticación desde el dispositivo
                if message_type == "auth":
                    token = message.get("token")
                    if token:
                        await manager.send_json(websocket, {
                            "type": "auth_response",
                            "success": True,
                            "message": "Autenticado correctamente"
                        })
                        print(f"🔐 Dispositivo {device_id} autenticado")
                
                # Manejar registro de tarjeta NFC desde el dispositivo
                elif message_type == "nfc_card_registered":
                    card_uid = message.get("card_uid")
                    user_id = message.get("user_id")
                    card_name = message.get("card_name")
                    
                    if card_uid and user_id:
                        # Aquí podrías procesar el registro de la tarjeta
                        print(f"🔄 Tarjeta {card_uid} registrada para usuario {user_id}")
                        
            except json.JSONDecodeError:
                print("❌ Mensaje no es JSON válido")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        manager.device_connections.pop(device_id, None)
        print(f"❌ Dispositivo {device_id} desconectado")