from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket_manager import manager
import json

router = APIRouter()

@router.websocket("/ws/device/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    # Conectar usando el método mejorado que acepta device_id
    await manager.connect(websocket, device_id=device_id)
    
    print(f"✅ Dispositivo {device_id} conectado vía WebSocket. Dispositivos activos: {len(manager.device_connections)}")

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
                        print(f"🔄 Tarjeta {card_uid} registrada para usuario {user_id}")
                        
                        # Confirmar registro exitoso al dispositivo
                        await manager.send_json(websocket, {
                            "type": "nfc_registration_success",
                            "success": True,
                            "message": f"Tarjeta {card_name} registrada exitosamente"
                        })
                
                # Manejar notificaciones de acceso desde el dispositivo
                elif message_type == "access_log":
                    print(f"📝 Log de acceso desde dispositivo {device_id}: {message}")
                
                # Manejar confirmación de acciones
                elif message_type == "action_confirmed":
                    action_id = message.get("action_id")
                    print(f"✅ Acción {action_id} confirmada por dispositivo {device_id}")
                
            except json.JSONDecodeError:
                print("❌ Mensaje no es JSON válido")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, device_id=device_id)
        print(f"❌ Dispositivo {device_id} desconectado. Dispositivos activos: {len(manager.device_connections)}")