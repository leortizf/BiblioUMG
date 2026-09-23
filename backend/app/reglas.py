"""
REGLAS DE NEGOCIO — el corazón del sistema (módulo crítico).

Aquí están todas las reglas de la biblioteca en funciones "puras":
reciben datos y devuelven un resultado, sin tocar la base de datos.
Eso las hace fáciles de probar con pytest en la fase 2.

Resumen de reglas:
  Tipo        Préstamos simultáneos  Días de préstamo  Renovaciones  Multa por día
  ESTUDIANTE  3                      7                 1             Q2.00
  DOCENTE     5                      14                2             Q1.00

  - Del día 1 al 7 de atraso se cobra la tarifa normal por día.
  - Desde el día 8 de atraso se cobra el DOBLE de la tarifa por cada día extra.
  - La multa de un préstamo nunca pasa de Q50.00 (tope).
  - Si un libro se devuelve con MÁS de 30 días de atraso, el usuario queda bloqueado.
  - Un usuario con multa pendiente o bloqueado no puede solicitar ni renovar.
"""
import re
from datetime import date

LIMITE_PRESTAMOS = {"ESTUDIANTE": 3, "DOCENTE": 5}
DIAS_PRESTAMO = {"ESTUDIANTE": 7, "DOCENTE": 14}
MAX_RENOVACIONES = {"ESTUDIANTE": 1, "DOCENTE": 2}
TARIFA_DIARIA = {"ESTUDIANTE": 2.00, "DOCENTE": 1.00}
TOPE_MULTA = 50.00
DIAS_TARIFA_NORMAL = 7
DIAS_PARA_BLOQUEO = 30
DIAS_MAX_REGISTRO_RETROACTIVO = 60
MIN_EJEMPLARES = 1
MAX_EJEMPLARES = 20
ANIO_MINIMO = 1450

# Estados que cuentan como "préstamo vigente" (ocupan cupo del usuario)
ESTADOS_VIGENTES = {"SOLICITADO", "ACTIVO", "RENOVADO", "VENCIDO"}

# Máquina de estados: desde cada estado, a cuáles se puede pasar.
TRANSICIONES = {
    "SOLICITADO": {"ACTIVO", "RECHAZADO", "CANCELADO"},
    "ACTIVO": {"RENOVADO", "VENCIDO", "DEVUELTO"},
    "RENOVADO": {"RENOVADO", "VENCIDO", "DEVUELTO"},
    "VENCIDO": {"DEVUELTO"},
    "DEVUELTO": set(),   # estado final
    "RECHAZADO": set(),  # estado final
    "CANCELADO": set(),  # estado final
}


# ---------------------------------------------------------------- estados
def transicion_valida(estado_actual: str, estado_nuevo: str) -> bool:
    """Indica si se permite pasar de un estado a otro."""
    return estado_nuevo in TRANSICIONES.get(estado_actual, set())


# ---------------------------------------------------------------- multas
def calcular_dias_atraso(fecha_vencimiento: date, fecha_devolucion: date) -> int:
    """Días entre el vencimiento y la devolución. Nunca negativo."""
    return max(0, (fecha_devolucion - fecha_vencimiento).days)


def calcular_multa(tipo_usuario: str, dias_atraso: int) -> float:
    """Calcula la multa según el tipo de usuario y los días de atraso."""
    if dias_atraso <= 0:
        return 0.0
    tarifa = TARIFA_DIARIA[tipo_usuario]
    if dias_atraso <= DIAS_TARIFA_NORMAL:
        multa = tarifa * dias_atraso
    else:
        dias_extra = dias_atraso - DIAS_TARIFA_NORMAL
        multa = tarifa * DIAS_TARIFA_NORMAL + (tarifa * 2) * dias_extra
    return round(min(multa, TOPE_MULTA), 2)


def debe_bloquearse(dias_atraso: int) -> bool:
    """Un atraso mayor a 30 días bloquea al usuario."""
    return dias_atraso > DIAS_PARA_BLOQUEO


# ---------------------------------------------------------------- préstamos
def puede_solicitar(tipo_usuario: str, prestamos_vigentes: int,
                    multa_pendiente: float, bloqueado: bool) -> tuple[bool, str]:
    """Decide si un usuario puede solicitar un nuevo préstamo."""
    if bloqueado:
        return False, "El usuario está bloqueado por atraso grave."
    if multa_pendiente > 0:
        return False, "El usuario tiene una multa pendiente de pago."
    if prestamos_vigentes >= LIMITE_PRESTAMOS[tipo_usuario]:
        return False, "El usuario alcanzó su límite de préstamos simultáneos."
    return True, "OK"


def puede_renovar(tipo_usuario: str, estado: str, renovaciones: int,
                  multa_pendiente: float, bloqueado: bool) -> tuple[bool, str]:
    """Decide si un préstamo puede renovarse."""
    if estado not in {"ACTIVO", "RENOVADO"}:
        return False, "Solo se pueden renovar préstamos activos o renovados."
    if bloqueado:
        return False, "El usuario está bloqueado por atraso grave."
    if multa_pendiente > 0:
        return False, "El usuario tiene una multa pendiente de pago."
    if renovaciones >= MAX_RENOVACIONES[tipo_usuario]:
        return False, "El préstamo alcanzó el máximo de renovaciones."
    return True, "OK"


def validar_fecha_registro(fecha: date, hoy: date) -> tuple[bool, str]:
    """Una fecha de entrega/devolución no puede ser futura ni de hace más de 60 días."""
    if fecha > hoy:
        return False, "La fecha no puede ser futura."
    if (hoy - fecha).days > DIAS_MAX_REGISTRO_RETROACTIVO:
        return False, "La fecha no puede ser de hace más de 60 días."
    return True, "OK"


# ---------------------------------------------------------------- validaciones
PATRON_CARNE = re.compile(r"^\d{4}-\d{2}-\d{3,6}$")


def validar_carne(carne: str) -> bool:
    """Formato UMG: 4 dígitos, guion, 2 dígitos, guion, 3 a 6 dígitos. Ej: 0901-22-12345"""
    return bool(PATRON_CARNE.match(carne or ""))


def validar_isbn13(isbn: str) -> bool:
    """Valida un ISBN-13: 13 dígitos y dígito verificador correcto."""
    if not isbn or len(isbn) != 13 or not isbn.isdigit():
        return False
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn[:12]))
    verificador = (10 - suma % 10) % 10
    return verificador == int(isbn[12])


def validar_anio(anio: int, anio_actual: int) -> bool:
    """El año de publicación debe estar entre 1450 y el año actual."""
    return ANIO_MINIMO <= anio <= anio_actual


def validar_ejemplares(cantidad: int) -> bool:
    """Un libro tiene entre 1 y 20 ejemplares."""
    return MIN_EJEMPLARES <= cantidad <= MAX_EJEMPLARES
