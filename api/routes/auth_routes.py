from fastapi import APIRouter, HTTPException, status
from schemas import LoginRequest, TokenResponse
from auth import USERS_DB, verify_password, create_access_token
from config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """
    Inicio de sesión para obtener token JWT de acceso.
    Permite autenticarse como 'admin' o 'viewer'.
    """
    user = USERS_DB.get(request.username)
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Verifique usuario y contraseña.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {"sub": user["username"], "role": user["role"]}
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        username=user["username"],
        role=user["role"],
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    )
