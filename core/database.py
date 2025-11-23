from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session  # ✅ Solo SQLAlchemy
from core.config import settings

# Motor de conexión a la base de datos
engine = create_engine(settings.DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    """Crea todas las tablas definidas en los modelos si no existen."""
    from models.users import User
    from models.devices import Device
    from models.tokens import Token
    from models.logs import Log
    from models.actions_devices import ActionDevice
    from models.nfc_cards import NFCCard
    from models.access_pins import AccessPin

    # Importar Base de SQLAlchemy desde alguno de los modelos
    from models.users import User
    User.metadata.create_all(engine)

def get_session():
    """Generador para obtener la sesión de la base de datos."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()