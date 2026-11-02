"""
Configuración compartida de pytest.

La fixture `cliente` levanta la API en memoria (TestClient) con una base SQLite
temporal y los datos iniciales. Cada prueba recibe una base limpia.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.seed import cargar_datos_iniciales


@pytest.fixture()
def cliente():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False},
                          poolclass=StaticPool)
    sesion = sessionmaker(bind=motor)
    Base.metadata.create_all(motor)
    with sesion() as db:
        cargar_datos_iniciales(db)

    def db_prueba():
        with sesion() as db:
            yield db

    app.dependency_overrides[get_db] = db_prueba
    yield TestClient(app)
    app.dependency_overrides.clear()


def token(c, email, password):
    respuesta = c.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": "Bearer " + respuesta.json()["token"]}


@pytest.fixture()
def estudiante(cliente):
    return token(cliente, "estudiante@biblioumg.com", "Estudiante123")


@pytest.fixture()
def admin(cliente):
    return token(cliente, "admin@biblioumg.com", "Admin12345")
