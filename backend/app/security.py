"""
Seguridad: cifrado de contraseñas y tokens de sesión (JWT).

- Las contraseñas nunca se guardan tal cual; se guarda un "hash" (huella).
- Al iniciar sesión se entrega un token JWT que el frontend envía en cada
  petición (encabezado Authorization: Bearer <token>).
"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-esta-clave-en-produccion")
ALGORITMO = "HS256"
HORAS_EXPIRACION = 8
ITERACIONES = 100_000

bearer = HTTPBearer(auto_error=False)


def hashear_password(password: str) -> str:
    sal = os.urandom(16)
    huella = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, ITERACIONES)
    return f"{sal.hex()}${huella.hex()}"


def verificar_password(password: str, guardado: str) -> bool:
    sal_hex, huella_hex = guardado.split("$")
    huella = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal_hex), ITERACIONES)
    return hmac.compare_digest(huella.hex(), huella_hex)


def crear_token(usuario: Usuario) -> str:
    datos = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "exp": datetime.now(timezone.utc) + timedelta(hours=HORAS_EXPIRACION),
    }
    return jwt.encode(datos, SECRET_KEY, algorithm=ALGORITMO)


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                   db: Session = Depends(get_db)) -> Usuario:
    """Obtiene el usuario que hace la petición a partir del token."""
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Debe iniciar sesión.")
    try:
        datos = jwt.decode(cred.credentials, SECRET_KEY, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada.")
    usuario = db.get(Usuario, int(datos["sub"]))
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado.")
    return usuario


def solo_bibliotecario(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Permite continuar solo si el usuario es bibliotecario."""
    if usuario.rol != "BIBLIOTECARIO":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acción exclusiva del bibliotecario.")
    return usuario
