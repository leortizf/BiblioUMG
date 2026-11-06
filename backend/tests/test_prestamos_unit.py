"""
Pruebas UNITARIAS de las funciones auxiliares del módulo crítico routers/prestamos.py.

Usan DOBLES DE PRUEBA:
- MagicMock reemplaza la sesión de base de datos (no se usa PostgreSQL).
- patch() reemplaza la fecha de "hoy" por una fija, para que la prueba
  dé el mismo resultado cualquier día que se ejecute.
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import Prestamo
from app.routers import prestamos


class FechaFija(date):
    """Stub de date: today() siempre devuelve el 30 de octubre de 2026."""
    @classmethod
    def today(cls):
        return cls(2026, 10, 30)


def test_cambiar_estado_valido():
    p = Prestamo(estado="SOLICITADO")
    prestamos.cambiar_estado(p, "ACTIVO")
    assert p.estado == "ACTIVO"


def test_cambiar_estado_invalido_responde_409_y_no_cambia():
    p = Prestamo(estado="CANCELADO")
    with pytest.raises(HTTPException) as error:
        prestamos.cambiar_estado(p, "ACTIVO")
    assert error.value.status_code == 409 and p.estado == "CANCELADO"


def test_obtener_prestamo_inexistente_responde_404():
    """MOCK: la base de datos no encuentra el préstamo."""
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(HTTPException) as error:
        prestamos.obtener_prestamo(db, 999)
    assert error.value.status_code == 404


@patch("app.routers.prestamos.date", FechaFija)
def test_validar_fecha_futura_responde_422():
    """STUB de fecha: 'hoy' es fijo, así mañana siempre es 31/10/2026."""
    with pytest.raises(HTTPException) as error:
        prestamos.validar_fecha(date(2026, 10, 31))
    assert error.value.status_code == 422


@patch("app.routers.prestamos.date", FechaFija)
def test_actualizar_vencidos_marca_y_guarda():
    """MOCK: la consulta devuelve dos préstamos atrasados; se verifica que se marquen y se guarde."""
    p1, p2 = Prestamo(estado="ACTIVO"), Prestamo(estado="RENOVADO")
    db = MagicMock()
    db.scalars.return_value.all.return_value = [p1, p2]
    prestamos.actualizar_vencidos(db)
    assert p1.estado == p2.estado == "VENCIDO"
    db.commit.assert_called_once()


def test_actualizar_vencidos_sin_pendientes_no_guarda():
    """MOCK: si no hay préstamos atrasados no se hace commit innecesario."""
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    prestamos.actualizar_vencidos(db)
    db.commit.assert_not_called()
