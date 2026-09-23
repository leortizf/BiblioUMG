"""
Modelos: cada clase representa una tabla de la base de datos.

Tablas:
- usuarios: personas que usan el sistema (estudiantes, docentes y bibliotecarios).
- libros: catálogo de la biblioteca con la cantidad de ejemplares.
- prestamos: cada préstamo de un libro a un usuario, con su estado.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    carne: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    # tipo: ESTUDIANTE o DOCENTE (define límites, días de préstamo y multas)
    tipo: Mapped[str] = mapped_column(String(20), default="ESTUDIANTE")
    # rol: USUARIO (presta libros) o BIBLIOTECARIO (administra)
    rol: Mapped[str] = mapped_column(String(20), default="USUARIO")
    multa_pendiente: Mapped[float] = mapped_column(Float, default=0.0)
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prestamos: Mapped[list["Prestamo"]] = relationship(back_populates="usuario")


class Libro(Base):
    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    autor: Mapped[str] = mapped_column(String(120))
    anio: Mapped[int] = mapped_column(Integer)
    ejemplares_totales: Mapped[int] = mapped_column(Integer, default=1)
    ejemplares_disponibles: Mapped[int] = mapped_column(Integer, default=1)

    prestamos: Mapped[list["Prestamo"]] = relationship(back_populates="libro")


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    libro_id: Mapped[int] = mapped_column(ForeignKey("libros.id"))
    # Estados posibles: SOLICITADO, ACTIVO, RENOVADO, VENCIDO,
    # DEVUELTO, RECHAZADO, CANCELADO (ver reglas.py)
    estado: Mapped[str] = mapped_column(String(20), default="SOLICITADO")
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_devolucion: Mapped[date | None] = mapped_column(Date, nullable=True)
    renovaciones: Mapped[int] = mapped_column(Integer, default=0)
    dias_atraso: Mapped[int] = mapped_column(Integer, default=0)
    multa: Mapped[float] = mapped_column(Float, default=0.0)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(200), nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="prestamos")
    libro: Mapped[Libro] = relationship(back_populates="prestamos")
