"""
Rutas de préstamos: el flujo principal del negocio.

Ciclo de vida de un préstamo (máquina de estados):

  SOLICITADO --entregar--> ACTIVO --renovar--> RENOVADO --renovar--> RENOVADO
      |                      |                    |
      |--rechazar--> RECHAZADO   (vence la fecha) |--> VENCIDO
      |--cancelar--> CANCELADO   ACTIVO/RENOVADO/VENCIDO --devolver--> DEVUELTO
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import reglas
from ..database import get_db
from ..models import Libro, Prestamo, Usuario
from ..schemas import FechaOpcionalIn, PrestamoIn, PrestamoOut, RechazoIn
from ..security import solo_bibliotecario, usuario_actual

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])


# ---------------------------------------------------------------- utilidades
def actualizar_vencidos(db: Session) -> None:
    """Marca como VENCIDO todo préstamo activo/renovado cuya fecha ya pasó."""
    hoy = date.today()
    pendientes = db.scalars(select(Prestamo).where(
        Prestamo.estado.in_(["ACTIVO", "RENOVADO"]),
        Prestamo.fecha_vencimiento < hoy)).all()
    for p in pendientes:
        p.estado = "VENCIDO"
    if pendientes:
        db.commit()


def obtener_prestamo(db: Session, prestamo_id: int) -> Prestamo:
    prestamo = db.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Préstamo no encontrado.")
    return prestamo


def cambiar_estado(prestamo: Prestamo, nuevo: str) -> None:
    """Aplica la máquina de estados: rechaza transiciones no permitidas."""
    if not reglas.transicion_valida(prestamo.estado, nuevo):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"No se puede pasar de {prestamo.estado} a {nuevo}.")
    prestamo.estado = nuevo


def validar_fecha(fecha: date) -> None:
    ok, motivo = reglas.validar_fecha_registro(fecha, date.today())
    if not ok:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, motivo)


# ---------------------------------------------------------------- usuario
@router.post("", response_model=PrestamoOut, status_code=201)
def solicitar(datos: PrestamoIn, db: Session = Depends(get_db),
              usuario: Usuario = Depends(usuario_actual)):
    """El usuario solicita un libro. Queda en estado SOLICITADO."""
    actualizar_vencidos(db)
    libro = db.get(Libro, datos.libro_id)
    if libro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Libro no encontrado.")
    if libro.ejemplares_disponibles <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "No hay ejemplares disponibles.")

    vigentes = db.scalar(select(func.count()).select_from(Prestamo).where(
        Prestamo.usuario_id == usuario.id, Prestamo.estado.in_(reglas.ESTADOS_VIGENTES)))
    ok, motivo = reglas.puede_solicitar(usuario.tipo, vigentes,
                                        usuario.multa_pendiente, usuario.bloqueado)
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, motivo)

    repetido = db.scalar(select(Prestamo).where(
        Prestamo.usuario_id == usuario.id, Prestamo.libro_id == libro.id,
        Prestamo.estado.in_(reglas.ESTADOS_VIGENTES)))
    if repetido:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya tiene un préstamo vigente de este libro.")

    prestamo = Prestamo(usuario_id=usuario.id, libro_id=libro.id, estado="SOLICITADO")
    db.add(prestamo)
    db.commit()
    db.refresh(prestamo)
    return prestamo


@router.get("/mios", response_model=list[PrestamoOut])
def mis_prestamos(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    actualizar_vencidos(db)
    return db.scalars(select(Prestamo).where(Prestamo.usuario_id == usuario.id)
                      .order_by(Prestamo.id.desc())).all()


@router.post("/{prestamo_id}/cancelar", response_model=PrestamoOut)
def cancelar(prestamo_id: int, db: Session = Depends(get_db),
             usuario: Usuario = Depends(usuario_actual)):
    """El usuario cancela su solicitud antes de recibir el libro."""
    prestamo = obtener_prestamo(db, prestamo_id)
    if prestamo.usuario_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puede cancelar sus propios préstamos.")
    cambiar_estado(prestamo, "CANCELADO")
    db.commit()
    db.refresh(prestamo)
    return prestamo


@router.post("/{prestamo_id}/renovar", response_model=PrestamoOut)
def renovar(prestamo_id: int, db: Session = Depends(get_db),
            usuario: Usuario = Depends(usuario_actual)):
    """Extiende la fecha de vencimiento por otro periodo completo."""
    actualizar_vencidos(db)
    prestamo = obtener_prestamo(db, prestamo_id)
    if prestamo.usuario_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puede renovar sus propios préstamos.")
    ok, motivo = reglas.puede_renovar(usuario.tipo, prestamo.estado, prestamo.renovaciones,
                                      usuario.multa_pendiente, usuario.bloqueado)
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, motivo)
    cambiar_estado(prestamo, "RENOVADO")
    prestamo.renovaciones += 1
    prestamo.fecha_vencimiento += timedelta(days=reglas.DIAS_PRESTAMO[usuario.tipo])
    db.commit()
    db.refresh(prestamo)
    return prestamo


# ---------------------------------------------------------------- bibliotecario
@router.get("", response_model=list[PrestamoOut])
def listar(estado: str | None = None, db: Session = Depends(get_db),
           _=Depends(solo_bibliotecario)):
    """Lista todos los préstamos. Con ?estado=ACTIVO filtra por estado."""
    actualizar_vencidos(db)
    consulta = select(Prestamo).order_by(Prestamo.id.desc())
    if estado:
        consulta = consulta.where(Prestamo.estado == estado.upper())
    return db.scalars(consulta).all()


@router.post("/{prestamo_id}/entregar", response_model=PrestamoOut)
def entregar(prestamo_id: int, datos: FechaOpcionalIn | None = None,
             db: Session = Depends(get_db), _=Depends(solo_bibliotecario)):
    """El bibliotecario entrega el libro. Se calcula la fecha de vencimiento."""
    prestamo = obtener_prestamo(db, prestamo_id)
    fecha = (datos.fecha if datos and datos.fecha else date.today())
    validar_fecha(fecha)
    if prestamo.libro.ejemplares_disponibles <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "No hay ejemplares disponibles para entregar.")
    cambiar_estado(prestamo, "ACTIVO")
    prestamo.fecha_entrega = fecha
    prestamo.fecha_vencimiento = fecha + timedelta(days=reglas.DIAS_PRESTAMO[prestamo.usuario.tipo])
    prestamo.libro.ejemplares_disponibles -= 1
    db.commit()
    actualizar_vencidos(db)  # si la fecha es retroactiva, podría quedar vencido de una vez
    db.refresh(prestamo)
    return prestamo


@router.post("/{prestamo_id}/rechazar", response_model=PrestamoOut)
def rechazar(prestamo_id: int, datos: RechazoIn, db: Session = Depends(get_db),
             _=Depends(solo_bibliotecario)):
    prestamo = obtener_prestamo(db, prestamo_id)
    cambiar_estado(prestamo, "RECHAZADO")
    prestamo.motivo_rechazo = datos.motivo
    db.commit()
    db.refresh(prestamo)
    return prestamo


@router.post("/{prestamo_id}/devolver", response_model=PrestamoOut)
def devolver(prestamo_id: int, datos: FechaOpcionalIn | None = None,
             db: Session = Depends(get_db), _=Depends(solo_bibliotecario)):
    """Registra la devolución, calcula atraso y multa, y bloquea si corresponde."""
    actualizar_vencidos(db)
    prestamo = obtener_prestamo(db, prestamo_id)
    fecha = (datos.fecha if datos and datos.fecha else date.today())
    validar_fecha(fecha)
    if prestamo.fecha_entrega and fecha < prestamo.fecha_entrega:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La devolución no puede ser anterior a la entrega.")
    cambiar_estado(prestamo, "DEVUELTO")

    prestamo.fecha_devolucion = fecha
    prestamo.dias_atraso = reglas.calcular_dias_atraso(prestamo.fecha_vencimiento, fecha)
    prestamo.multa = reglas.calcular_multa(prestamo.usuario.tipo, prestamo.dias_atraso)
    prestamo.usuario.multa_pendiente = round(prestamo.usuario.multa_pendiente + prestamo.multa, 2)
    if reglas.debe_bloquearse(prestamo.dias_atraso):
        prestamo.usuario.bloqueado = True
    prestamo.libro.ejemplares_disponibles += 1
    db.commit()
    db.refresh(prestamo)
    return prestamo
