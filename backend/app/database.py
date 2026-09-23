"""
Conexión a la base de datos.

- En tu computadora (local) se usa SQLite: un archivo llamado biblioteca.db.
- En la nube (Render) se usa PostgreSQL de Neon, indicado en la variable
  de entorno DATABASE_URL.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biblioteca.db")

# Neon entrega URLs que empiezan con "postgres://" o "postgresql://".
# SQLAlchemy necesita saber que usaremos el controlador "psycopg".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base de la que heredan todas las tablas (modelos)."""


def get_db():
    """Abre una sesión de base de datos por cada petición y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
