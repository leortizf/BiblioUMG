"""
Rutas de autenticación (registro, login) y administración de usuarios.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Usuario
from ..schemas import LoginIn, PagoMultaIn, RegistroIn, TokenOut, UsuarioOut
from ..security import (crear_token, hashear_password, solo_bibliotecario,
                        usuario_actual, verificar_password)

router = APIRouter(tags=["Usuarios"])


@router.post("/auth/registro", response_model=UsuarioOut, status_code=201)
def registrar(datos: RegistroIn, db: Session = Depends(get_db)):
    """Crea una cuenta nueva de estudiante o docente."""
    if db.scalar(select(Usuario).where(Usuario.email == datos.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese correo.")
    if db.scalar(select(Usuario).where(Usuario.carne == datos.carne)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese carné.")
    usuario = Usuario(
        nombre=datos.nombre.strip(),
        carne=datos.carne,
        email=datos.email.lower(),
        password_hash=hashear_password(datos.password),
        tipo=datos.tipo,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/auth/login", response_model=TokenOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    """Inicia sesión y devuelve un token."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == datos.email.lower()))
    if usuario is None or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos.")
    return {"token": crear_token(usuario), "usuario": usuario}


@router.get("/auth/yo", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual)):
    """Devuelve los datos del usuario que inició sesión."""
    return usuario


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _=Depends(solo_bibliotecario)):
    return db.scalars(select(Usuario).order_by(Usuario.nombre)).all()


@router.post("/usuarios/{usuario_id}/pagar-multa", response_model=UsuarioOut)
def pagar_multa(usuario_id: int, pago: PagoMultaIn, db: Session = Depends(get_db),
                _=Depends(solo_bibliotecario)):
    """Registra un pago (total o parcial) de la multa pendiente."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if usuario.multa_pendiente <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "El usuario no tiene multa pendiente.")
    if pago.monto > usuario.multa_pendiente:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "El monto no puede ser mayor que la multa pendiente.")
    usuario.multa_pendiente = round(usuario.multa_pendiente - pago.monto, 2)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/usuarios/{usuario_id}/desbloquear", response_model=UsuarioOut)
def desbloquear(usuario_id: int, db: Session = Depends(get_db), _=Depends(solo_bibliotecario)):
    """Quita el bloqueo, solo si el usuario ya no debe multas."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if not usuario.bloqueado:
        raise HTTPException(status.HTTP_409_CONFLICT, "El usuario no está bloqueado.")
    if usuario.multa_pendiente > 0:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Debe pagar la multa completa antes de desbloquearse.")
    usuario.bloqueado = False
    db.commit()
    db.refresh(usuario)
    return usuario
