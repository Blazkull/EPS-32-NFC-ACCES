from fastapi import APIRouter, Depends
from sqlmodel import Session, text
from core.database import get_session

router = APIRouter(prefix="/health", tags=["Health Check"])

@router.get("/")
def health_check(session: Session = Depends(get_session)):
    """
    Verifica el estado de conexión del backend y la base de datos.
    """
    try:
        session.exec(text("SELECT 1"))
        return {
            "status": "ok",
            "backend": "online",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "backend": "offline",
            "database": f"error: {str(e)}"
        }