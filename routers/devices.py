from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from sqlalchemy.orm import Session  # ✅ SQLAlchemy
from core.database import get_session
from core.security import get_current_user
from models.devices import Device
from schemas.devices_schema import DeviceCreate, DeviceRead, DeviceUpdate, DeviceUpdateIP, DeviceStatusUpdate

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(
    data: DeviceCreate, 
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Crear un nuevo dispositivo con validaciones de seguridad."""
    
    # ✅ CORREGIDO: Usar session.query()
    existing_device = session.query(Device).filter(Device.name == data.name).first()
    
    if existing_device:
        raise HTTPException(status_code=400, detail="Ya existe un dispositivo con ese nombre")

    new_device = Device(
        name=data.name,
        status=data.status or "offline",
        direction=data.direction,
        nfc_reader_active=getattr(data, 'nfc_reader_active', True),
        emergency_mode=getattr(data, 'emergency_mode', False),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    session.add(new_device)
    session.commit()
    session.refresh(new_device)
    
    return new_device

@router.get("/", response_model=List[DeviceRead])
def list_devices(
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
    status_filter: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Obtiene una lista de dispositivos con filtros seguros."""
    
    if limit > 100:
        limit = 100
    
    # ✅ CORREGIDO: Usar session.query()
    query = session.query(Device)
    
    if status_filter:
        query = query.filter(Device.status == status_filter)
    
    if name:
        query = query.filter(Device.name.ilike(f"%{name}%"))

    results = query.offset(offset).limit(limit).all()
    return results

@router.get("/{device_id}", response_model=DeviceRead)
def get_device(
    device_id: int, 
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Obtener un dispositivo específico por ID."""
    
    # ✅ CORREGIDO: Usar session.query()
    device = session.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    return device

@router.put("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int, 
    data: DeviceUpdate, 
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Actualizar dispositivo con validaciones de seguridad."""
    
    # ✅ CORREGIDO: Usar session.query()
    device = session.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(device, key, value)
    
    device.updated_at = datetime.utcnow()
    session.add(device)
    session.commit()
    session.refresh(device)
    
    return device

@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int, 
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
):
    """Eliminar dispositivo con validaciones de seguridad."""
    
    # ✅ CORREGIDO: Usar session.query()
    device = session.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    session.delete(device)
    session.commit()
    return