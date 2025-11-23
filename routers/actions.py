from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_session
from core.security import get_current_user
from models.actions_devices import ActionDevice
from models.devices import Device
from models.logs import Log
from models.users import User
from schemas.actions_schema import ActionDeviceCreate, ActionDeviceRead, ActionDeviceUpdate
from core.whatsapp_service import whatsapp_service

router = APIRouter(prefix="/actions", tags=["Actions Devices"])

async def enviar_notificacion_whatsapp(action_type: str, user_id: int, session: Session):
    """Envía notificación por WhatsApp cuando se abre una puerta"""
    try:
        # Obtener información del usuario
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print("⚠️ Usuario no encontrado para notificación WhatsApp")
            return
        
        user_name = user.name
        door_name = "PUERTA PRINCIPAL" if action_type == "DOOR_OPEN" else "GARAJE"
        
        # Enviar notificación
        success = await whatsapp_service.send_access_notification(
            user_name=user_name,
            access_type="APERTURA REMOTA",
            door=door_name
        )
        
        if success:
            print(f"✅ Notificación WhatsApp enviada para {user_name} - {door_name}")
        else:
            print(f"❌ Error enviando notificación WhatsApp para {user_name}")
            
    except Exception as e:
        print(f"❌ Error en notificación WhatsApp: {e}")

@router.post("/", response_model=ActionDeviceRead)
async def create_action(
    data: ActionDeviceCreate,
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Crea una acción para un dispositivo específico."""
    print(f"📥 Datos recibidos: {data.dict()}")
    
    device = session.query(Device).filter(Device.id == data.id_device).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    new_action = ActionDevice(
        id_device=data.id_device,
        action=data.action,
        executed=False,
        created_at=datetime.utcnow(),
    )
    
    session.add(new_action)
    session.commit()
    session.refresh(new_action)

    # <<< NUEVO: Enviar notificación WhatsApp si es apertura de puerta >>>
    if data.action in ["DOOR_OPEN", "GARAGE_OPEN"]:
        await enviar_notificacion_whatsapp(data.action, user.id, session)

    # Enviar al WebSocket
    from core.websocket_manager import manager
    payload = {
        "type": "action_execute",
        "action_id": new_action.id,
        "id_device": new_action.id_device,
        "action_type": new_action.action,
        "timestamp": new_action.created_at.isoformat(),
    }
    
    try:
        await manager.send_to_device(data.id_device, payload)
        print(f"✅ Acción enviada por WebSocket al dispositivo {data.id_device}")
    except Exception as e:
        print(f"⚠️ No se pudo enviar al dispositivo {data.id_device}: {e}")

    # Crear log
    log = Log(
        id_device=data.id_device,
        id_user=user.id,
        id_action=new_action.id,
        event=f"Acción '{data.action}' creada para dispositivo {data.id_device}",
        access_type="remote"
    )
    session.add(log)
    session.commit()

    print(f"✅ Acción creada exitosamente: ID {new_action.id}")
    return new_action

@router.put("/{action_id}", response_model=ActionDeviceRead)
async def update_action_status(
    action_id: int,
    update: ActionDeviceUpdate,
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Actualiza el estado (ejecutada) de una acción."""
    action = session.query(ActionDevice).filter(ActionDevice.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Acción no encontrada")

    if update.executed is not None:
        action.executed = update.executed

    session.add(action)

    log_message = "Acción ejecutada correctamente" if action.executed else "Acción marcada como no ejecutada"

    log = Log(
        id_device=action.id_device,
        id_user=user.id,
        id_action=action.id,
        event=log_message,
        access_type="remote"
    )
    session.add(log)
    session.commit()
    session.refresh(action)

    # Notificar por WebSocket
    from core.websocket_manager import manager
    payload = {
        "event": "action_updated",
        "action_id": action.id,
        "id_device": action.id_device,
        "status": "executed" if action.executed else "pending",
    }
    
    try:
        await manager.send_to_device(action.id_device, payload)
    except Exception as e:
        print(f"⚠️ No se pudo notificar actualización al dispositivo: {e}")

    return action

@router.get("/", response_model=list[ActionDeviceRead])
def list_actions(
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
    id_device: int | None = None,
    executed: bool | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Obtiene todas las acciones con filtros opcionales."""
    query = session.query(ActionDevice)
    if id_device:
        query = query.filter(ActionDevice.id_device == id_device)
    if executed is not None:
        query = query.filter(ActionDevice.executed == executed)

    results = query.offset(offset).limit(limit).all()
    return results

@router.get("/{action_id}", response_model=ActionDeviceRead)
def get_action(
    action_id: int,
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Obtiene una acción específica por su ID."""
    action = session.query(ActionDevice).filter(ActionDevice.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Acción no encontrada")
    return action

@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(
    action_id: int,
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Elimina una acción por su ID."""
    action = session.query(ActionDevice).filter(ActionDevice.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Acción no encontrada")

    session.delete(action)
    session.commit()
    return

@router.post("/device/confirm/{action_id}")
async def confirm_action_execution(
    action_id: int,
    session: Session = Depends(get_session),
):
    """
    Endpoint llamado por el IoT (ESP32, Arduino, etc.)
    cuando confirma que la acción fue ejecutada físicamente.
    """
    action = session.query(ActionDevice).filter(ActionDevice.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Acción no encontrada")

    action.executed = True
    session.add(action)

    log = Log(
        id_device=action.id_device,
        id_user=None,
        id_action=action.id,
        event=f"Dispositivo confirmó ejecución de acción '{action.action}'",
        access_type="remote"
    )
    session.add(log)
    session.commit()

    from core.websocket_manager import manager
    payload = {
        "event": "action_confirmed",
        "action_id": action.id,
        "id_device": action.id_device,
        "action_type": action.action,
        "status": "executed",
    }
    
    try:
        await manager.broadcast_json(payload)
    except Exception as e:
        print(f"⚠️ Error al broadcast confirmación: {e}")

    return {"message": "Acción confirmada por el dispositivo", "action_id": action.id}

@router.post("/access-log")
async def log_access_and_notify(
    data: dict,
    session: Session = Depends(get_session),
):
    """
    Endpoint para registrar accesos locales (desde Arduino) y enviar notificaciones WhatsApp
    """
    try:
        print(f"📥 Log de acceso recibido: {data}")
        
        user_id = data.get("id_user", 0)
        user_name = data.get("user_name", "Usuario Local")
        action_type = data.get("action", "UNKNOWN")
        access_type = data.get("access_type", "local")
        
        # Determinar nombre de la puerta
        door_name = "PUERTA PRINCIPAL" if action_type == "DOOR_OPEN" else "GARAJE"
        
        # Enviar notificación WhatsApp
        success = await whatsapp_service.send_access_notification(
            user_name=user_name,
            access_type=f"APERTURA {access_type.upper()}",
            door=door_name
        )
        
        if success:
            print(f"✅ Notificación WhatsApp enviada para acceso local: {user_name} - {door_name}")
        else:
            print(f"❌ Error enviando notificación WhatsApp para acceso local")
        
        # Crear log en base de datos
        log = Log(
            id_device=data.get("id_device", 1),
            id_user=user_id if user_id != 0 else None,
            id_action=None,
            event=f"Acceso {access_type}: {user_name} abrió {door_name}",
            access_type=access_type
        )
        session.add(log)
        session.commit()
        
        return {
            "success": True,
            "message": "Acceso registrado y notificación enviada",
            "notification_sent": success
        }
        
    except Exception as e:
        print(f"❌ Error en log de acceso: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando acceso: {str(e)}")