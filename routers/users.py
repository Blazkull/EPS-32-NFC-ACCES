from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from sqlalchemy.orm import Session  # ✅ SQLAlchemy
from datetime import datetime
from core.database import get_session
from core.security import get_current_user
from models.users import User
from schemas.users_schema import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=List[UserRead])
def get_users(
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Obtiene todos los usuarios (requiere autenticación)"""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    users = session.query(User).all()
    print(f"📋 Usuario {user.username} consultó {len(users)} usuarios")
    return users

@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int, 
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Obtiene un usuario específico por ID"""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    user_data = session.query(User).filter(User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    print(f"🔍 Usuario {user.username} consultó usuario ID: {user_id}")
    return user_data

@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, 
    data: UserUpdate, 
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Actualiza un usuario específico"""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    user_data = session.query(User).filter(User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar que el usuario solo pueda editar su propio perfil o tenga permisos de admin
    if user.id != user_id and user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar este usuario"
        )
    
    # Actualizar campos
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'password' and value:
            from core.security import hash_password
            setattr(user_data, key, hash_password(value))
        else:
            setattr(user_data, key, value)
    
    user_data.updated_at = datetime.utcnow()
    session.add(user_data)
    session.commit()
    session.refresh(user_data)
    
    print(f"✏️ Usuario {user.username} actualizó usuario ID: {user_id}")
    return user_data

@router.delete("/{user_id}")
def delete_user(
    user_id: int, 
    session: Session = Depends(get_session),  # ✅ SQLAlchemy Session
    user = Depends(get_current_user),
):
    """Elimina un usuario específico"""
    # ✅ CORREGIDO: Usar session.query() de SQLAlchemy
    user_data = session.query(User).filter(User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar permisos (solo admin puede eliminar usuarios)
    if user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede eliminar usuarios"
        )
    
    # No permitir auto-eliminación
    if user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario"
        )
    
    session.delete(user_data)
    session.commit()
    
    print(f"🗑️ Usuario {user.username} eliminó usuario ID: {user_id}")
    return {"message": "Usuario eliminado correctamente"}

@router.get("/me/profile", response_model=UserRead)
def get_my_profile(
    user = Depends(get_current_user),
):
    """Obtiene el perfil del usuario actualmente autenticado"""
    return user