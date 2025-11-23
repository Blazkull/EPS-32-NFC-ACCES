from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session  # ✅ Solo SQLAlchemy
import bcrypt

from core.config import settings
from core.database import get_session
from models.users import User
from models.tokens import Token as DBToken

# ------------------- CONFIGURACIÓN OAUTH2 -------------------
outh2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# ---------------------- FUNCIONES DE PASSWORD ----------------------
def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al hashear contraseña: {str(e)}"
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash."""
    try:
        print(f"🔐 DEBUG - Verificando contraseña:")
        print(f"   Contraseña ingresada: '{plain_password}'")
        print(f"   Hash almacenado: {hashed_password}")
        
        # Verificar que el hash tenga el formato correcto
        if not hashed_password.startswith('$2b$'):
            print(f"❌ ERROR: Formato de hash inválido")
            return False
        
        # Verificar la contraseña
        result = bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
        
        print(f"✅ DEBUG - Resultado verificación: {result}")
        return result
        
    except Exception as e:
        print(f"❌ ERROR en verify_password: {e}")
        return False

# ---------------------- FUNCIONES JWT TOKEN ----------------------
def create_access_token(data: dict):
    """Crea un token JWT de acceso."""
    try:
        # Crear copia de los datos para no modificar el original
        to_encode = data.copy()
        
        # Calcular tiempo de expiración
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        
        # Codificar token
        token = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return token, expire
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando token: {str(e)}"
        )

def decode_token(token: str, session: Session):
    """
    Decodifica y valida un token JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Verificar que tenga username
        username: str = payload.get("username")
        if username is None:
            raise credentials_exception
        
        # Verificar expiración
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None:
            raise credentials_exception
            
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        if exp_datetime < datetime.now(timezone.utc):
            raise expired_exception
            
    except JWTError as e:
        print(f"❌ Error JWT: {e}")
        raise expired_exception
    except Exception as e:
        print(f"❌ Error decodificando token: {e}")
        raise credentials_exception

    # Buscar usuario en base de datos
    try:
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise credentials_exception
        
        # Verificar que el usuario esté activo
        if not user.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario desactivado"
            )
            
    except Exception as e:
        print(f"❌ Error buscando usuario: {e}")
        raise credentials_exception

    # Verificar que el token esté activo en la base de datos
    try:
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        db_token = session.query(DBToken).filter(
            DBToken.token == token, 
            DBToken.status_token == True,
            DBToken.expiration > datetime.utcnow()
        ).first()
        
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )
            
    except Exception as e:
        print(f"❌ Error verificando token en BD: {e}")
        raise credentials_exception

    return user

def get_current_user(token: str = Depends(outh2_scheme), session: Session = Depends(get_session)):
    """
    Función para obtener el usuario actual como dependencia FastAPI.
    """
    return decode_token(token, session)

def validate_token(token: str, session: Session) -> dict:
    """
    Valida un token sin usar dependencias de FastAPI.
    Útil para validaciones fuera de endpoints.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("username")
        
        if not username:
            return {"valid": False, "error": "Token inválido"}
        
        # Verificar expiración
        exp_timestamp = payload.get("exp")
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) < datetime.now(timezone.utc):
            return {"valid": False, "error": "Token expirado"}
        
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        user = session.query(User).filter(User.username == username).first()
        if not user or not user.status:
            return {"valid": False, "error": "Usuario no válido"}
        
        # ✅ CORREGIDO: Usar SQLAlchemy session.query()
        db_token = session.query(DBToken).filter(
            DBToken.token == token, 
            DBToken.status_token == True
        ).first()
        
        if not db_token:
            return {"valid": False, "error": "Token no encontrado en BD"}
        
        return {
            "valid": True, 
            "user": user,
            "payload": payload
        }
        
    except JWTError as e:
        return {"valid": False, "error": f"Error JWT: {str(e)}"}
    except Exception as e:
        return {"valid": False, "error": f"Error validando token: {str(e)}"}

# ---------------------- FUNCIONES DE SEGURIDAD ADICIONALES ----------------------
def create_password_reset_token(email: str) -> str:
    """Crea un token para restablecimiento de contraseña."""
    try:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)  # 30 minutos para reset
        to_encode = {
            "sub": email,
            "type": "password_reset",
            "exp": expire
        }
        
        token = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return token
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando token de reset: {str(e)}"
        )

def verify_password_reset_token(token: str) -> str:
    """Verifica un token de restablecimiento de contraseña."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if not email or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de reset inválido"
            )
        
        # Verificar expiración
        exp_timestamp = payload.get("exp")
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de reset expirado"
            )
        
        return email
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de reset inválido"
        )

def generate_api_key(user_id: int) -> str:
    """Genera una API key para un usuario."""
    try:
        expire = datetime.now(timezone.utc) + timedelta(days=365)  # 1 año
        to_encode = {
            "user_id": user_id,
            "type": "api_key",
            "exp": expire
        }
        
        api_key = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return api_key
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando API key: {str(e)}"
        )

# ---------------------- FUNCIONES DE VALIDACIÓN ----------------------
def is_strong_password(password: str) -> dict:
    """
    Valida la fortaleza de una contraseña.
    Retorna dict con 'valid' y 'message'.
    """
    if len(password) < 8:
        return {"valid": False, "message": "La contraseña debe tener al menos 8 caracteres"}
    
    if not any(char.isdigit() for char in password):
        return {"valid": False, "message": "La contraseña debe contener al menos un número"}
    
    if not any(char.isupper() for char in password):
        return {"valid": False, "message": "La contraseña debe contener al menos una mayúscula"}
    
    if not any(char.islower() for char in password):
        return {"valid": False, "message": "La contraseña debe contener al menos una minúscula"}
    
    # Caracteres especiales opcionales pero recomendados
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return {
            "valid": True, 
            "message": "Contraseña aceptada (se recomienda añadir caracteres especiales)"
        }
    
    return {"valid": True, "message": "Contraseña fuerte"}

def sanitize_input(input_string: str, max_length: int = 255) -> str:
    """
    Sanitiza una cadena de entrada para prevenir inyecciones.
    """
    if not input_string:
        return ""
    
    # Limitar longitud
    if len(input_string) > max_length:
        input_string = input_string[:max_length]
    
    # Eliminar caracteres potencialmente peligrosos
    dangerous_chars = ['<', '>', 'script', 'javascript', 'onload', 'onerror']
    for char in dangerous_chars:
        input_string = input_string.replace(char, '')
    
    # Eliminar espacios en blanco extra
    input_string = ' '.join(input_string.split())
    
    return input_string

# ---------------------- FUNCIONES DE AUDITORÍA ----------------------
def log_security_event(session: Session, event: str, user_id: int = None, details: str = None):
    """
    Registra un evento de seguridad en los logs.
    """
    try:
        from models.logs import Log
        
        log_entry = Log(
            id_device=1,  # Sistema principal
            id_user=user_id,
            event=f"SEGURIDAD: {event}",
            access_type="security",
            timestamp=datetime.utcnow()
        )
        
        if details:
            log_entry.event += f" - {details}"
        
        session.add(log_entry)
        session.commit()
        
    except Exception as e:
        print(f"❌ Error registrando evento de seguridad: {e}")
        # No lanzar excepción para no interrumpir el flujo principal