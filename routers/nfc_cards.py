from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # ✅ SQLAlchemy
from datetime import datetime
from typing import List

from core.database import get_session
from core.security import get_current_user
from models.nfc_cards import NFCCard
from models.users import User
from models.logs import Log
from schemas.nfc_schema import (
    NFCCardCreate, NFCCardRead, NFCCardUpdate, 
    NFCCardValidation, NFCRegistrationRequest
)

router = APIRouter(prefix="/nfc-cards", tags=["NFC Cards"])

@router.post("/", response_model=NFCCardRead)
async def create_nfc_card(
    data: NFCCardCreate,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Crea una nueva tarjeta NFC asociada a un usuario."""
    
    # Verificar que el usuario exista
    user_data = session.query(User).filter(User.id == data.id_user).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    existing_card = session.query(NFCCard).filter(NFCCard.card_uid == data.card_uid).first()
    if existing_card:
        raise HTTPException(status_code=400, detail="La tarjeta NFC ya está registrada")

    new_card = NFCCard(
        card_uid=data.card_uid,
        id_user=data.id_user,
        card_name=data.card_name,
        status=data.status
    )
    
    session.add(new_card)
    
    # Crear log
    log = Log(
        id_device=1,
        id_user=user.id,
        event=f"Tarjeta NFC '{data.card_name}' creada para usuario {user_data.name}",
        access_type="remote"
    )
    session.add(log)
    
    session.commit()
    session.refresh(new_card)

    return new_card

@router.get("/", response_model=List[NFCCardRead])
def get_nfc_cards(
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Obtiene todas las tarjetas NFC."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    return session.query(NFCCard).all()

@router.get("/{card_id}", response_model=NFCCardRead)
def get_nfc_card(
    card_id: int,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Obtiene una tarjeta NFC específica."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    card = session.query(NFCCard).filter(NFCCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta NFC no encontrada")
    return card

@router.put("/{card_id}", response_model=NFCCardRead)
def update_nfc_card(
    card_id: int,
    data: NFCCardUpdate,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Actualiza una tarjeta NFC."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    card = session.query(NFCCard).filter(NFCCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta NFC no encontrada")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(card, key, value)
    
    card.updated_at = datetime.utcnow()
    session.add(card)
    session.commit()
    session.refresh(card)

    return card

@router.delete("/{card_id}")
def delete_nfc_card(
    card_id: int,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Elimina una tarjeta NFC."""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    card = session.query(NFCCard).filter(NFCCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta NFC no encontrada")

    session.delete(card)
    session.commit()
    return {"message": "Tarjeta NFC eliminada correctamente"}

@router.post("/validate", response_model=NFCCardValidation)
async def validate_nfc_card(
    card_uid: str,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
):
    """Valida una tarjeta NFC (usado por el ESP32)."""
    
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    card = session.query(NFCCard).filter(
        NFCCard.card_uid == card_uid,
        NFCCard.status == True
    ).first()

    if not card:
        return NFCCardValidation(
            valid=False,
            message="Tarjeta no válida o desactivada"
        )

    user = session.query(User).filter(User.id == card.id_user).first()
    if not user or not user.status:
        return NFCCardValidation(
            valid=False,
            message="Usuario desactivado"
        )

    # Verificar estado del dispositivo
    from models.devices import Device
    device = session.query(Device).filter(Device.id == 1).first()  # Dispositivo principal
    if device and not device.nfc_reader_active:
        return NFCCardValidation(
            valid=False,
            message="Lector NFC desactivado - Sistema fuera de servicio"
        )

    # Crear log de acceso
    log = Log(
        id_device=1,
        id_user=user.id,
        event=f"Acceso concedido vía NFC - Tarjeta: {card.card_name}",
        access_type="nfc"
    )
    session.add(log)
    session.commit()

    # Notificar por WebSocket al dispositivo
    try:
        from core.websocket_manager import manager
        await manager.send_to_device(1, {
            "type": "nfc_access",
            "valid": True,
            "user_name": user.name,
            "card_name": card.card_name,
            "message": f"Bienvenido {user.name}"
        })
    except Exception as e:
        print(f"⚠️ Error notificando acceso NFC: {e}")

    return NFCCardValidation(
        valid=True,
        card=card,
        user=user,
        message=f"Acceso concedido - Bienvenido {user.name}"
    )

@router.post("/register-card")
async def register_nfc_card(
    data: NFCRegistrationRequest,
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Inicia el proceso de registro de una nueva tarjeta NFC."""
    
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    user_data = session.query(User).filter(User.id == data.user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Notificar al dispositivo para que espere la tarjeta
    try:
        from core.websocket_manager import manager
        await manager.send_to_device(1, {
            "type": "nfc_registration",
            "user_id": data.user_id,
            "user_name": user_data.name,
            "card_name": data.card_name,
            "message": "Acerca la tarjeta NFC para registrar"
        })
        return {"message": "Solicitud de registro enviada al dispositivo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error comunicándose con el dispositivo")