from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    VIEWER_USERNAME,
    VIEWER_PASSWORD,
)

security = HTTPBearer(auto_error=False)

# Usuarios sembrados en memoria / configuración
USERS_DB = {
    ADMIN_USERNAME: {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "role": "admin",
    },
    VIEWER_USERNAME: {
        "username": VIEWER_USERNAME,
        "password": VIEWER_PASSWORD,
        "role": "viewer",
    },
}


def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verifica si la contraseña coincide (admite texto plano y hash bcrypt)."""
    if plain_password == stored_password:
        return True
    try:
        if stored_password.startswith("$2b$") or stored_password.startswith("$2a$"):
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_password.encode("utf-8"))
    except Exception:
        pass
    return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Genera un JWT firmado criptográficamente."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Valida y decodifica el token JWT."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de sesión ha expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """Dependencia FastAPI que extrae el usuario autenticado del token Bearer."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Proporcione un token Bearer válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado o sin claims de identidad.",
        )
    return {"username": username, "role": role}


def require_viewer(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Permite el acceso a roles viewer y admin."""
    if current_user.get("role") not in ("viewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes para acceder a este recurso.",
        )
    return current_user


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Permite el acceso exclusivamente a rol admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acción restringida. Se requiere rol de Administrador.",
        )
    return current_user
