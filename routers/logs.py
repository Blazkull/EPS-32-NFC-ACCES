from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session  # ✅ SQLAlchemy
from sqlalchemy import func, or_
from typing import Optional, Dict, List, Any
from core.database import get_session
from core.security import get_current_user
from models.logs import Log
from models.devices import Device
from schemas.logs_schema import LogReadPaginated

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("/", response_model=LogReadPaginated)
def get_logs(
    session: Session = Depends(get_session),
    user = Depends(get_current_user),
    id_device: Optional[int] = None,
    event_contains: Optional[str] = Query(None, description="Filtrar logs cuyo evento contenga esta cadena."),
    access_type: Optional[str] = None,
    id_action: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Obtiene logs con filtros, paginación y recuentos por dispositivo, estado y tipo de acción.
    """
    
    # ✅ CORREGIDO: Usar session.query()
    query = session.query(Log)

    if id_device:
        query = query.filter(Log.id_device == id_device)
    
    if event_contains:
        query = query.filter(Log.event.ilike(f"%{event_contains}%"))
        
    if access_type:
        query = query.filter(Log.access_type == access_type)
        
    if id_action: 
        query = query.filter(Log.id_action == id_action)
    
    # Ejecutar consulta para obtener total y datos paginados
    total = query.count()
    
    offset = (page - 1) * limit
    logs = query.offset(offset).limit(limit).all()

    pages = (total // limit) + (1 if total % limit > 0 else 0)

    return LogReadPaginated(
        total=total,
        page=page,
        limit=limit,
        pages=pages,
        data=logs,
        counts_by_device={},
        counts_by_status={},
        counts_by_action_type={},
        counts_by_access_type={},
    )