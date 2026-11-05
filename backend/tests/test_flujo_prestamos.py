"""
Pruebas de COMPONENTE de routers/prestamos.py con pytest.

No son pruebas unitarias puras: la API se ejecuta en memoria (TestClient, fixture
`cliente` de conftest.py) con una base SQLite temporal en lugar de PostgreSQL.
Así se prueban las rutas con sus reglas sin red ni servidor real.
"""
from datetime import date, timedelta


def test_flujo_solicitar_entregar_renovar_devolver(cliente, estudiante, admin):
    p = cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante).json()
    assert p["estado"] == "SOLICITADO"
    p = cliente.post(f"/prestamos/{p['id']}/entregar", headers=admin).json()
    assert p["estado"] == "ACTIVO" and p["libro"]["ejemplares_disponibles"] == 2
    p = cliente.post(f"/prestamos/{p['id']}/renovar", headers=estudiante).json()
    assert p["estado"] == "RENOVADO" and p["renovaciones"] == 1
    p = cliente.post(f"/prestamos/{p['id']}/devolver", headers=admin).json()
    assert p["estado"] == "DEVUELTO" and p["multa"] == 0 and p["libro"]["ejemplares_disponibles"] == 3


def test_cuarto_prestamo_de_estudiante_rechazado(cliente, estudiante):
    for libro in (1, 2, 3):
        assert cliente.post("/prestamos", json={"libro_id": libro}, headers=estudiante).status_code == 201
    r = cliente.post("/prestamos", json={"libro_id": 4}, headers=estudiante)
    assert r.status_code == 409 and "límite" in r.json()["detail"]


def test_devolucion_con_31_dias_de_atraso_bloquea(cliente, estudiante, admin):
    p = cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante).json()
    entrega = (date.today() - timedelta(days=38)).isoformat()
    cliente.post(f"/prestamos/{p['id']}/entregar", json={"fecha": entrega}, headers=admin)
    p = cliente.post(f"/prestamos/{p['id']}/devolver", headers=admin).json()
    assert p["dias_atraso"] == 31 and p["multa"] == 50 and p["usuario"]["bloqueado"] is True


def test_cancelar_y_luego_entregar_responde_409(cliente, estudiante, admin):
    p = cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante).json()
    assert cliente.post(f"/prestamos/{p['id']}/cancelar", headers=estudiante).json()["estado"] == "CANCELADO"
    assert cliente.post(f"/prestamos/{p['id']}/entregar", headers=admin).status_code == 409


def test_rechazar_solicitud_con_motivo(cliente, estudiante, admin):
    p = cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante).json()
    r = cliente.post(f"/prestamos/{p['id']}/rechazar", json={"motivo": "Ejemplar en reparación"}, headers=admin)
    assert r.json()["estado"] == "RECHAZADO"


def test_estudiante_no_puede_listar_todos_los_prestamos(cliente, estudiante):
    assert cliente.get("/prestamos", headers=estudiante).status_code == 403


def test_bibliotecario_filtra_prestamos_por_estado(cliente, estudiante, admin):
    cliente.post("/prestamos", json={"libro_id": 1}, headers=estudiante)
    lista = cliente.get("/prestamos?estado=solicitado", headers=admin).json()
    assert len(lista) == 1 and lista[0]["estado"] == "SOLICITADO"
    assert cliente.get("/prestamos/mios", headers=estudiante).json()[0]["libro"]["id"] == 1
