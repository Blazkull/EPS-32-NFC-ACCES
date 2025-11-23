from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # ✅ SQLAlchemy
from datetime import datetime
from typing import List

from core.database import get_session
from core.security import get_current_user
from models.access_pins import AccessPin
from models.users import User
from models.logs import Log
from schemas.pins_schema import (
    AccessPinCreate, AccessPinRead, AccessPinUpdate, 
    PinValidation, PinVerification
)

router = APIRouter(prefix="/access-pins", tags=["Access Pins"])

@router.post("/", response_model=AccessPinRead)
async def create_access_pin(
    data: AccessPinCreate,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Crea un nuevo PIN de acceso asociado a un usuario."""
    
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    user_data = session.query(User).filter(User.id == data.id_user).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar que el usuario no tenga ya un PIN activo
    existing_pin = session.query(AccessPin).filter(
        AccessPin.id_user == data.id_user,
        AccessPin.status == True
    ).first()
    if existing_pin:
        raise HTTPException(status_code=400, detail="El usuario ya tiene un PIN activo")

    new_pin = AccessPin(
        id_user=data.id_user,
        pin_code=data.pin_code,
        status=data.status
    )
    
    session.add(new_pin)
    
    # Crear log
    log = Log(
        id_device=1,
        id_user=user.id,
        event=f"PIN de acceso creado para usuario {user_data.name}",
        access_type="remote"
    )
    session.add(log)
    
    session.commit()
    session.refresh(new_pin)

    return new_pin

@router.get("/", response_model=List[AccessPinRead])
def get_access_pins(
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Obtiene todos los PINs de acceso."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    return session.query(AccessPin).all()

@router.get("/{pin_id}", response_model=AccessPinRead)
def get_access_pin(
    pin_id: int,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Obtiene un PIN de acceso específico."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    pin = session.query(AccessPin).filter(AccessPin.id == pin_id).first()
    if not pin:
        raise HTTPException(status_code=404, detail="PIN de acceso no encontrado")
    return pin

@router.put("/{pin_id}", response_model=AccessPinRead)
async def update_access_pin(
    pin_id: int,
    data: AccessPinUpdate,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Actualiza un PIN de acceso."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    pin = session.query(AccessPin).filter(AccessPin.id == pin_id).first()
    if not pin:
        raise HTTPException(status_code=404, detail="PIN de acceso no encontrado")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(pin, key, value)
    
    pin.updated_at = datetime.utcnow()
    session.add(pin)
    session.commit()
    session.refresh(pin)

    return pin

@router.delete("/{pin_id}")
def delete_access_pin(
    pin_id: int,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Elimina un PIN de acceso."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    pin = session.query(AccessPin).filter(AccessPin.id == pin_id).first()
    if not pin:
        raise HTTPException(status_code=404, detail="PIN de acceso no encontrado")

    session.delete(pin)
    session.commit()
    return {"message": "PIN de acceso eliminado correctamente"}

@router.post("/validate", response_model=PinValidation)
async def validate_pin(
    pin_code: str,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
):
    """Valida un PIN de acceso (usado por el ESP32)."""
    
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    pin = session.query(AccessPin).filter(
        AccessPin.pin_code == pin_code,
        AccessPin.status == True
    ).first()

    if not pin:
        return PinValidation(
            valid=False,
            message="PIN no válido o desactivado"
        )

    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    user = session.query(User).filter(User.id == pin.id_user).first()
    if not user or not user.status:
        return PinValidation(
            valid=False,
            message="Usuario desactivado"
        )

    # Verificar estado del dispositivo
    from models.devices import Device
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    device = session.query(Device).filter(Device.id == 1).first()
    if device and not device.nfc_reader_active:
        return PinValidation(
            valid=False,
            message="Sistema desactivado - Modo emergencia"
        )

    # Crear log de acceso
    log = Log(
        id_device=1,
        id_user=user.id,
        event=f"Acceso concedido vía PIN - Usuario: {user.name}",
        access_type="pin"
    )
    session.add(log)
    session.commit()

    # Notificar por WebSocket al dispositivo
    try:
        from core.websocket_manager import manager
        await manager.send_to_device(1, {
            "type": "pin_access",
            "valid": True,
            "user_name": user.name,
            "message": f"Bienvenido {user.name}"
        })
    except Exception as e:
        print(f"⚠️ Error notificando acceso PIN: {e}")

    return PinValidation(
        valid=True,
        pin=pin,
        user=user,
        message=f"Acceso concedido - Bienvenido {user.name}"
    )

@router.post("/verify")
async def verify_pin(
    data: PinVerification,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Verifica un PIN antes de realizar cambios (para seguridad)."""
    
    # Buscar el PIN del usuario actual
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    pin = session.query(AccessPin).filter(
        AccessPin.id_user == user.id,
        AccessPin.status == True
    ).first()

    if not pin:
        raise HTTPException(status_code=404, detail="No se encontró PIN activo para el usuario")

    if pin.pin_code != data.pin_code:
        raise HTTPException(status_code=400, detail="PIN incorrecto")

    return {"valid": True, "message": "PIN verificado correctamente"}