"""
Pruebas UNITARIAS del módulo crítico reglas.py.

Cada prueba verifica una función pura (sin base de datos ni red), de forma aislada.
Los valores elegidos siguen las mismas técnicas de la fase 1:
valores límite (7/8 días, 30/31 días, 1/20 ejemplares) y tablas de decisión.
"""
from datetime import date

import pytest

from app import reglas


# ---------------------------------------------------------------- multas
@pytest.mark.parametrize("tipo, dias, esperado", [
    ("ESTUDIANTE", 0, 0.0),     # sin atraso
    ("ESTUDIANTE", 1, 2.0),     # primer día de atraso
    ("ESTUDIANTE", 7, 14.0),    # último día de tarifa normal (límite)
    ("ESTUDIANTE", 8, 18.0),    # primer día de tarifa doble (límite)
    ("ESTUDIANTE", 16, 50.0),   # alcanza exactamente el tope
    ("ESTUDIANTE", 40, 50.0),   # sobrepasa el tope
    ("DOCENTE", 7, 7.0),
    ("DOCENTE", 8, 9.0),
    ("DOCENTE", 28, 49.0),      # justo debajo del tope
    ("DOCENTE", 29, 50.0),      # tope (sin tope serían Q51.00)
])
def test_calcular_multa(tipo, dias, esperado):
    assert reglas.calcular_multa(tipo, dias) == esperado


def test_multa_con_dias_negativos_es_cero():
    assert reglas.calcular_multa("ESTUDIANTE", -3) == 0.0


def test_dias_atraso_cuando_devuelve_tarde():
    assert reglas.calcular_dias_atraso(date(2026, 10, 1), date(2026, 10, 9)) == 8


def test_dias_atraso_nunca_negativo_si_devuelve_antes():
    assert reglas.calcular_dias_atraso(date(2026, 10, 10), date(2026, 10, 5)) == 0


@pytest.mark.parametrize("dias, bloquea", [(30, False), (31, True)])
def test_bloqueo_por_atraso_limite_30_dias(dias, bloquea):
    assert reglas.debe_bloquearse(dias) is bloquea


# ---------------------------------------------------------------- estados
@pytest.mark.parametrize("actual, nuevo", [
    ("SOLICITADO", "ACTIVO"), ("SOLICITADO", "RECHAZADO"), ("SOLICITADO", "CANCELADO"),
    ("ACTIVO", "RENOVADO"), ("ACTIVO", "VENCIDO"), ("ACTIVO", "DEVUELTO"),
    ("RENOVADO", "RENOVADO"), ("VENCIDO", "DEVUELTO"),
])
def test_transiciones_validas(actual, nuevo):
    assert reglas.transicion_valida(actual, nuevo)


@pytest.mark.parametrize("actual, nuevo", [
    ("CANCELADO", "ACTIVO"), ("VENCIDO", "RENOVADO"), ("DEVUELTO", "ACTIVO"),
    ("RECHAZADO", "ACTIVO"), ("SOLICITADO", "DEVUELTO"), ("ESTADO_INEXISTENTE", "ACTIVO"),
])
def test_transiciones_invalidas(actual, nuevo):
    assert not reglas.transicion_valida(actual, nuevo)


# ---------------------------------------------------------------- tabla de decisión: solicitar
def test_puede_solicitar_regla_r1_permitido():
    assert reglas.puede_solicitar("ESTUDIANTE", 2, 0, False) == (True, "OK")


def test_puede_solicitar_regla_r2_bloqueado():
    ok, motivo = reglas.puede_solicitar("ESTUDIANTE", 0, 0, True)
    assert not ok and "bloqueado" in motivo


def test_puede_solicitar_regla_r3_multa():
    ok, motivo = reglas.puede_solicitar("DOCENTE", 0, 5.0, False)
    assert not ok and "multa" in motivo


@pytest.mark.parametrize("tipo, vigentes", [("ESTUDIANTE", 3), ("DOCENTE", 5)])
def test_puede_solicitar_regla_r4_limite(tipo, vigentes):
    ok, motivo = reglas.puede_solicitar(tipo, vigentes, 0, False)
    assert not ok and "límite" in motivo


# ---------------------------------------------------------------- tabla de decisión: renovar
def test_renovar_estudiante_primera_vez():
    assert reglas.puede_renovar("ESTUDIANTE", "ACTIVO", 0, 0, False)[0]


def test_renovar_estudiante_segunda_vez_rechazada():
    assert not reglas.puede_renovar("ESTUDIANTE", "RENOVADO", 1, 0, False)[0]


def test_renovar_docente_segunda_vez_permitida():
    assert reglas.puede_renovar("DOCENTE", "RENOVADO", 1, 0, False)[0]


def test_renovar_prestamo_vencido_rechazado():
    ok, motivo = reglas.puede_renovar("DOCENTE", "VENCIDO", 0, 0, False)
    assert not ok and "activos" in motivo


def test_renovar_con_multa_o_bloqueo_rechazado():
    assert not reglas.puede_renovar("DOCENTE", "ACTIVO", 0, 1.0, False)[0]
    assert not reglas.puede_renovar("DOCENTE", "ACTIVO", 0, 0, True)[0]


# ---------------------------------------------------------------- fechas
HOY = date(2026, 10, 30)


@pytest.mark.parametrize("dias_atras, valida", [(0, True), (60, True), (61, False), (-1, False)])
def test_validar_fecha_registro(dias_atras, valida):
    from datetime import timedelta
    assert reglas.validar_fecha_registro(HOY - timedelta(days=dias_atras), HOY)[0] is valida


# ---------------------------------------------------------------- validaciones de datos
@pytest.mark.parametrize("carne, valido", [
    ("0901-22-123", True), ("0901-22-123456", True), ("0901-22-12", False),
    ("0901-22-1234567", False), ("0901-AB-12345", False), ("", False), (None, False),
])
def test_validar_carne(carne, valido):
    assert reglas.validar_carne(carne) is valido


@pytest.mark.parametrize("isbn, valido", [
    ("9785260181591", True), ("9780306406157", True), ("9785260181592", False),
    ("978526018159", False), ("978526018159X", False), ("", False),
])
def test_validar_isbn13(isbn, valido):
    assert reglas.validar_isbn13(isbn) is valido


@pytest.mark.parametrize("anio, valido", [(1449, False), (1450, True), (2026, True), (2027, False)])
def test_validar_anio(anio, valido):
    assert reglas.validar_anio(anio, 2026) is valido


@pytest.mark.parametrize("cantidad, valido", [(0, False), (1, True), (20, True), (21, False)])
def test_validar_ejemplares(cantidad, valido):
    assert reglas.validar_ejemplares(cantidad) is valido
