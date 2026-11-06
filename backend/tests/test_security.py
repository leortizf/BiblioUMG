"""
Pruebas UNITARIAS del módulo crítico security.py.

Usan DOBLES DE PRUEBA (mocks): la base de datos se reemplaza por un objeto
falso (MagicMock) para probar la lógica de autenticación sin conectarse a
PostgreSQL. Justificación: la prueba debe verificar solo la regla de seguridad,
no la base de datos, y debe ser rápida y repetible dentro del pipeline.
"""
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import security
from app.models import Usuario


def credenciales(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def usuario_falso(rol="USUARIO"):
    return Usuario(id=7, nombre="Prueba", carne="0901-26-1001", email="p@p.com",
                   password_hash="x", tipo="ESTUDIANTE", rol=rol)


def test_hash_no_guarda_la_contrasena_en_texto_plano():
    guardado = security.hashear_password("Estudiante123")
    assert "Estudiante123" not in guardado
    sal, huella = guardado.split("$")
    assert len(sal) == 32 and len(huella) == 64   # 16 bytes de sal, SHA-256


def test_hash_usa_sal_aleatoria():
    """La misma contraseña cifrada dos veces da resultados distintos (sal aleatoria)."""
    primer_hash = security.hashear_password("igual")
    segundo_hash = security.hashear_password("igual")
    assert primer_hash != segundo_hash

def test_verificar_password_correcta_e_incorrecta():
    guardado = security.hashear_password("Clave2026")
    assert security.verificar_password("Clave2026", guardado)
    assert not security.verificar_password("Clave2027", guardado)


def test_token_contiene_usuario_rol_y_expiracion():
    datos = jwt.decode(security.crear_token(usuario_falso("BIBLIOTECARIO")),
                       security.SECRET_KEY, algorithms=[security.ALGORITMO])
    assert datos["sub"] == "7" and datos["rol"] == "BIBLIOTECARIO" and "exp" in datos


def test_usuario_actual_con_token_valido_consulta_la_bd_mock():
    """MOCK: la sesión de base de datos es falsa y devuelve un usuario fijo."""
    db = MagicMock()
    db.get.return_value = usuario_falso()
    token = security.crear_token(usuario_falso())
    assert security.usuario_actual(credenciales(token), db).id == 7
    db.get.assert_called_once_with(Usuario, 7)   # verifica que se consultó el id correcto


def test_usuario_actual_sin_token_responde_401():
    db = MagicMock()
    with pytest.raises(HTTPException) as error:
        security.usuario_actual(None, db)
    assert error.value.status_code == 401
    db.get.assert_not_called()                   # ni siquiera llega a la base de datos


def test_usuario_actual_con_token_alterado_responde_401():
    db = MagicMock()
    token = security.crear_token(usuario_falso()) + "x"
    with pytest.raises(HTTPException) as error:
        security.usuario_actual(credenciales(token), db)
    assert error.value.status_code == 401


def test_usuario_actual_si_el_usuario_ya_no_existe_responde_401():
    """MOCK: simula que el usuario fue borrado (la base devuelve None)."""
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(HTTPException) as error:
        security.usuario_actual(credenciales(security.crear_token(usuario_falso())), db)
    assert error.value.status_code == 401


def test_solo_bibliotecario_rechaza_estudiante_con_403():
    with pytest.raises(HTTPException) as error:
        security.solo_bibliotecario(usuario_falso("USUARIO"))
    assert error.value.status_code == 403


def test_solo_bibliotecario_permite_bibliotecario():
    assert security.solo_bibliotecario(usuario_falso("BIBLIOTECARIO")).rol == "BIBLIOTECARIO"
