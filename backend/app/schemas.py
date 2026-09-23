"""
Esquemas: definen qué datos recibe y devuelve la API.
Si un dato no cumple, FastAPI responde automáticamente con error 422.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from . import reglas


# ---------------------------------------------------------------- usuarios
class RegistroIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=100)
    carne: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    tipo: Literal["ESTUDIANTE", "DOCENTE"] = "ESTUDIANTE"

    @field_validator("carne")
    @classmethod
    def carne_valido(cls, v: str) -> str:
        if not reglas.validar_carne(v):
            raise ValueError("El carné debe tener el formato 0000-00-00000.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    carne: str
    email: str
    tipo: str
    rol: str
    multa_pendiente: float
    bloqueado: bool


class TokenOut(BaseModel):
    token: str
    usuario: UsuarioOut


class PagoMultaIn(BaseModel):
    monto: float = Field(gt=0)


# ---------------------------------------------------------------- libros
class LibroIn(BaseModel):
    isbn: str
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=120)
    anio: int
    ejemplares_totales: int

    @field_validator("isbn")
    @classmethod
    def isbn_valido(cls, v: str) -> str:
        v = v.replace("-", "").strip()
        if not reglas.validar_isbn13(v):
            raise ValueError("El ISBN debe tener 13 dígitos y un dígito verificador válido.")
        return v

    @field_validator("anio")
    @classmethod
    def anio_valido(cls, v: int) -> int:
        if not reglas.validar_anio(v, date.today().year):
            raise ValueError(f"El año debe estar entre {reglas.ANIO_MINIMO} y el año actual.")
        return v

    @field_validator("ejemplares_totales")
    @classmethod
    def ejemplares_validos(cls, v: int) -> int:
        if not reglas.validar_ejemplares(v):
            raise ValueError("Un libro debe tener entre 1 y 20 ejemplares.")
        return v


class LibroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    isbn: str
    titulo: str
    autor: str
    anio: int
    ejemplares_totales: int
    ejemplares_disponibles: int


# ---------------------------------------------------------------- préstamos
class PrestamoIn(BaseModel):
    libro_id: int


class FechaOpcionalIn(BaseModel):
    """Permite registrar una entrega/devolución con fecha anterior (registro retroactivo)."""
    fecha: date | None = None


class RechazoIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=200)


class PrestamoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    estado: str
    fecha_solicitud: datetime
    fecha_entrega: date | None
    fecha_vencimiento: date | None
    fecha_devolucion: date | None
    renovaciones: int
    dias_atraso: int
    multa: float
    motivo_rechazo: str | None
    libro: LibroOut
    usuario: UsuarioOut
