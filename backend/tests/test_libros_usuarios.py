"""
Pruebas de COMPONENTE de routers/libros.py y routers/usuarios.py.

Usan la API en memoria con SQLite temporal (fixture `cliente` de conftest.py).
Cubren las reglas del catálogo (ISBN, ejemplares, eliminación) y de usuarios
(registro, pagos de multa, desbloqueo).
"""
from datetime import date, timedelta

LIBRO_NUEVO = {"isbn": "9780306406157", "titulo": "Libro de prueba", "autor": "Autora Prueba",
               "anio": 2020, "ejemplares_totales": 2}


# ---------------------------------------------------------------- libros
def test_buscar_libro_por_autor(cliente):
    resultado = cliente.get("/libros?q=Tzul").json()
    assert [l["titulo"] for l in resultado] == ["Historia de Guatemala"]


def test_obtener_libro_existente_e_inexistente(cliente):
    assert cliente.get("/libros/1").status_code == 200
    r = cliente.get("/libros/9999")
    assert r.status_code == 404 and r.json()["detail"] == "Libro no encontrado."


def test_crear_libro_acepta_isbn_con_guiones(cliente, admin):
    r = cliente.post("/libros", json={**LIBRO_NUEVO, "isbn": "978-0-306-40615-7"}, headers=admin)
    assert r.status_code == 201 and r.json()["isbn"] == "9780306406157"
    assert r.json()["ejemplares_disponibles"] == 2


def test_crear_libro_con_isbn_duplicado_responde_409(cliente, admin):
    cliente.post("/libros", json=LIBRO_NUEVO, headers=admin)
    assert cliente.post("/libros", json=LIBRO_NUEVO, headers=admin).status_code == 409


def test_crear_libro_con_datos_invalidos_responde_422(cliente, admin):
    for cambio in ({"isbn": "9780306406158"}, {"anio": 1449}, {"ejemplares_totales": 21}):
        assert cliente.post("/libros", json={**LIBRO_NUEVO, **cambio}, headers=admin).status_code == 422


def test_estudiante_no_puede_crear_libros(cliente, estudiante):
    assert cliente.post("/libros", json=LIBRO_NUEVO, headers=estudiante).status_code == 403


def test_editar_libro_y_no_reducir_bajo_prestados(cliente, estudiante, admin):
    p = cliente.post("/prestamos", json={"libro_id": 2}, headers=estudiante).json()
    cliente.post(f"/prestamos/{p['id']}/entregar", headers=admin)
    libro = cliente.get("/libros/2").json()
    datos = {k: libro[k] for k in ("isbn", "titulo", "autor", "anio")}
    r = cliente.put("/libros/2", json={**datos, "ejemplares_totales": 5}, headers=admin)
    assert r.status_code == 200 and r.json()["ejemplares_disponibles"] == 4
    assert cliente.put("/libros/2", json={**datos, "ejemplares_totales": 0}, headers=admin).status_code == 422
    assert cliente.put("/libros/9999", json={**datos, "ejemplares_totales": 5}, headers=admin).status_code == 404


def test_editar_libro_con_isbn_de_otro_responde_409(cliente, admin):
    libro = cliente.get("/libros/2").json()
    datos = {k: libro[k] for k in ("titulo", "autor", "anio", "ejemplares_totales")}
    isbn_del_libro_1 = cliente.get("/libros/1").json()["isbn"]
    assert cliente.put("/libros/2", json={**datos, "isbn": isbn_del_libro_1}, headers=admin).status_code == 409


def test_eliminar_libro_sin_historial(cliente, admin):
    nuevo = cliente.post("/libros", json=LIBRO_NUEVO, headers=admin).json()
    assert cliente.delete(f"/libros/{nuevo['id']}", headers=admin).status_code == 204
    assert cliente.delete(f"/libros/{nuevo['id']}", headers=admin).status_code == 404


def test_no_eliminar_libro_con_prestamo_vigente_o_historial(cliente, estudiante, admin):
    p = cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante).json()
    assert "vigentes" in cliente.delete("/libros/1", headers=admin).json()["detail"]
    cliente.post(f"/prestamos/{p['id']}/cancelar", headers=estudiante)
    assert "historial" in cliente.delete("/libros/1", headers=admin).json()["detail"]


# ---------------------------------------------------------------- usuarios
def test_registro_y_duplicados(cliente):
    datos = {"nombre": "Ana Prueba", "carne": "0901-26-1001", "email": "ana@prueba.com", "password": "Clave2026"}
    assert cliente.post("/auth/registro", json=datos).status_code == 201
    assert cliente.post("/auth/registro", json=datos).status_code == 409
    otro_correo = {**datos, "email": "otra@prueba.com"}
    assert "carné" in cliente.post("/auth/registro", json=otro_correo).json()["detail"]


def test_login_incorrecto_responde_401(cliente):
    r = cliente.post("/auth/login", json={"email": "admin@biblioumg.com", "password": "Incorrecta1"})
    assert r.status_code == 401


def test_bibliotecario_lista_usuarios(cliente, admin):
    assert len(cliente.get("/usuarios", headers=admin).json()) == 3


def _usuario_bloqueado_con_multa(cliente, estudiante, admin):
    """Prepara al estudiante con un atraso de 31 días: multa Q50.00 y bloqueo."""
    p = cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante).json()
    entrega = (date.today() - timedelta(days=38)).isoformat()
    cliente.post(f"/prestamos/{p['id']}/entregar", json={"fecha": entrega}, headers=admin)
    return cliente.post(f"/prestamos/{p['id']}/devolver", headers=admin).json()["usuario"]["id"]


def test_pago_de_multa_y_desbloqueo(cliente, estudiante, admin):
    uid = _usuario_bloqueado_con_multa(cliente, estudiante, admin)
    assert cliente.post(f"/usuarios/{uid}/desbloquear", headers=admin).status_code == 409
    assert cliente.post(f"/usuarios/{uid}/pagar-multa", json={"monto": 50.01}, headers=admin).status_code == 422
    assert cliente.post(f"/usuarios/{uid}/pagar-multa", json={"monto": 20}, headers=admin).json()["multa_pendiente"] == 30
    assert cliente.post(f"/usuarios/{uid}/pagar-multa", json={"monto": 30}, headers=admin).json()["multa_pendiente"] == 0
    assert cliente.post(f"/usuarios/{uid}/pagar-multa", json={"monto": 1}, headers=admin).status_code == 409
    assert cliente.post(f"/usuarios/{uid}/desbloquear", headers=admin).json()["bloqueado"] is False
    assert cliente.post(f"/usuarios/{uid}/desbloquear", headers=admin).status_code == 409


def test_pagos_y_desbloqueo_de_usuario_inexistente(cliente, admin):
    assert cliente.post("/usuarios/999/pagar-multa", json={"monto": 1}, headers=admin).status_code == 404
    assert cliente.post("/usuarios/999/desbloquear", headers=admin).status_code == 404
