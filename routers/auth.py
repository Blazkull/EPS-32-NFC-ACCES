from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session  # ✅ SQLAlchemy
from datetime import datetime, timezone

from core.database import get_session
from core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_user,
    outh2_scheme,
    is_strong_password,
    log_security_event
)
from models.users import User
from models.tokens import Token as DBToken
from models.logs import Log
from schemas.users_schema import UserCreate, UserRead, UserData
from schemas.auth_schema import LoginResponse
from core.websocket_manager import manager
from core.whatsapp_service import whatsapp_service

# ------------------- CONFIGURACIÓN DEL ROUTER -------------------
router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ------------------- REGISTRO DE USUARIO CORREGIDO -------------------
@router.post("/register", response_model=UserRead)
def register_user(user: UserCreate, session: Session = Depends(get_session)):
    """Registra un nuevo usuario en la base de datos."""
    
    try:
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        existing_user = session.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="El usuario ya existe")

        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        existing_email = session.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="El email ya está registrado")

        # Validar fortaleza de contraseña
        password_strength = is_strong_password(user.password)
        if not password_strength["valid"]:
            raise HTTPException(status_code=400, detail=password_strength["message"])

        # Hashear contraseña
        hashed_pw = hash_password(user.password)
        
        # Crear nuevo usuario
        new_user = User(
            username=user.username,
            password=hashed_pw,
            email=user.email,
            name=user.name,
            status=user.status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        # Crear log de registro
        log = Log(
            id_device=1,
            id_user=new_user.id,
            event=f"Usuario registrado: {user.username}",
            access_type="remote"
        )
        session.add(log)
        session.commit()
        
        print(f"✅ Nuevo usuario registrado: {user.username}")
        
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print(f"❌ Error en registro de usuario: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor durante el registro"
        )


# ------------------- LOGIN CORREGIDO -------------------
@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """
    Autentica al usuario y genera un token JWT.
    """
    try:
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        user = session.query(User).filter(User.username == form_data.username).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

        # Verificar estado del usuario
        if not user.status:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario desactivado")

        # Validar contraseña
        if not verify_password(form_data.password, user.password):
            log_security_event(session, "Intento de login fallido", user.id, f"Usuario: {user.username}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")

        # Crear token JWT
        token_data = {
            "sub": user.username,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "user_id": user.id
        }
        token, expire = create_access_token(token_data)

        # Guardar token en base de datos
        db_token = DBToken(
            id_user=user.id,
            token=token,
            status_token=True,
            date_token=datetime.now(timezone.utc),
            expiration=expire
        )
        session.add(db_token)

        # Actualizar última conexión
        user.last_connection = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        session.add(user)

        # Crear log de login exitoso
        log = Log(
            id_device=1,
            id_user=user.id,
            event=f"Login exitoso - Usuario: {user.username}",
            access_type="remote"
        )
        session.add(log)
        session.commit()

        # Enviar notificación WhatsApp
        try:
            await whatsapp_service.send_access_notification(
                user_name=user.name,
                access_type="Login Web",
                door="Panel de Control"
            )
        except Exception as e:
            print(f"⚠️ Error enviando notificación WhatsApp: {e}")

        # Notificar al dispositivo IoT
        try:
            await manager.send_to_device(1, {
                "type": "login",
                "success": True,
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "email": user.email
                }
            })
            print(f"✅ Notificación de login enviada al IoT")
        except Exception as e:
            print(f"⚠️ No se pudo notificar al IoT: {e}")

        # Crear objeto UserData para la respuesta
        user_data = UserData(
            id=user.id,
            username=user.username,
            name=user.name,
            email=user.email
        )

        log_security_event(session, "Login exitoso", user.id)

        # Respuesta al cliente web/app
        return {
            "success": True,
            "message": "Login exitoso",
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expire,
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print(f"❌ Error en login: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor durante el login"
        )


# ------------------- LOGOUT CORREGIDO -------------------
@router.post("/logout")
def logout(token: str = Depends(outh2_scheme), session: Session = Depends(get_session)):
    """Invalida un token activo."""
    try:
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        db_token = session.query(DBToken).filter(
            DBToken.token == token, 
            DBToken.status_token == True
        ).first()
        
        if not db_token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token no encontrado o ya invalidado")

        # Invalidar token
        db_token.status_token = False
        db_token.expiration = datetime.utcnow()
        session.add(db_token)

        # Crear log de logout
        log = Log(
            id_device=1,
            id_user=db_token.id_user,
            event="Logout exitoso",
            access_type="remote"
        )
        session.add(log)
        session.commit()
        
        print(f"✅ Logout exitoso para usuario ID: {db_token.id_user}")
        
        return {"success": True, "message": "Sesión cerrada correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print(f"❌ Error en logout: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor durante el logout"
        )


# ------------------- VERIFICACIÓN DE TOKEN -------------------
@router.get("/verify")
def verify_token(user = Depends(get_current_user)):
    """Verifica si un token es válido."""
    user_data = UserData(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email
    )
    
    return {
        "valid": True,
        "user": user_data
    }


# ------------------- RENOVACIÓN DE TOKEN CORREGIDO -------------------
@router.post("/refresh")
async def refresh_token(user = Depends(get_current_user), session: Session = Depends(get_session)):
    """Renueva el token de acceso."""
    try:
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        old_token = session.query(DBToken).filter(
            DBToken.id_user == user.id, 
            DBToken.status_token == True
        ).first()
        
        if old_token:
            old_token.status_token = False
            session.add(old_token)

        # Crear nuevo token
        token_data = {
            "sub": user.username,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "user_id": user.id
        }
        new_token, expire = create_access_token(token_data)

        # Guardar nuevo token
        db_token = DBToken(
            id_user=user.id,
            token=new_token,
            status_token=True,
            date_token=datetime.now(timezone.utc),
            expiration=expire
        )
        session.add(db_token)

        # Crear log
        log = Log(
            id_device=1,
            id_user=user.id,
            event="Token renovado exitosamente",
            access_type="remote"
        )
        session.add(log)
        session.commit()

        # Crear objeto UserData para la respuesta
        user_data = UserData(
            id=user.id,
            username=user.username,
            name=user.name,
            email=user.email
        )

        # Notificar renovación al dispositivo IoT
        try:
            await manager.send_to_device(1, {
                "type": "token_refreshed",
                "user_id": user.id,
                "new_token": new_token
            })
        except Exception as e:
            print(f"⚠️ No se pudo notificar renovación al IoT: {e}")

        return {
            "success": True,
            "message": "Token renovado exitosamente",
            "access_token": new_token,
            "token_type": "bearer",
            "expires_at": expire,
            "user": user_data
        }
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error en renovación de token: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor durante la renovación del token"
        )


# ------------------- CAMBIO DE CONTRASEÑA CORREGIDO -------------------
@router.post("/change-password")
def change_password(
    current_password: str,
    new_password: str,
    user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cambia la contraseña del usuario actual."""
    try:
        # Verificar contraseña actual
        if not verify_password(current_password, user.password):
            log_security_event(session, "Intento de cambio de contraseña fallido", user.id)
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

        # Validar fortaleza de nueva contraseña
        password_strength = is_strong_password(new_password)
        if not password_strength["valid"]:
            raise HTTPException(status_code=400, detail=password_strength["message"])

        # Hashear nueva contraseña
        hashed_new_password = hash_password(new_password)
        
        # Actualizar contraseña
        user.password = hashed_new_password
        user.updated_at = datetime.utcnow()
        session.add(user)

        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        tokens = session.query(DBToken).filter(
            DBToken.id_user == user.id, 
            DBToken.status_token == True
        ).all()
        
        for token in tokens:
            token.status_token = False
            session.add(token)

        # Crear log
        log = Log(
            id_device=1,
            id_user=user.id,
            event="Contraseña cambiada exitosamente",
            access_type="remote"
        )
        session.add(log)
        session.commit()

        log_security_event(session, "Contraseña cambiada exitosamente", user.id)

        return {"success": True, "message": "Contraseña cambiada exitosamente. Se ha cerrado la sesión en todos los dispositivos."}
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print(f"❌ Error en cambio de contraseña: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor durante el cambio de contraseña"
        )
    

@router.post("/test-password")
async def test_password(username: str, password: str, session: Session = Depends(get_session)):
    """Endpoint temporal para debug de contraseñas"""
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            return {"error": "Usuario no encontrado"}
        
        print(f"🔐 DEBUG TEST:")
        print(f"   Usuario: {user.username}")
        print(f"   Hash en BD: {user.password}")
        print(f"   Contraseña a verificar: '{password}'")
        
        # Probar verificación
        from core.security import verify_password
        is_valid = verify_password(password, user.password)
        
        return {
            "usuario": user.username,
            "hash_en_bd": user.password,
            "contraseña_ingresada": password,
            "es_valida": is_valid
        }
        
    except Exception as e:
        return {"error": str(e)}