"""
Punto de entrada del backend (API REST con FastAPI).

Para ejecutar en tu computadora:
    uvicorn app.main:app --reload
Documentación interactiva de la API: http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .routers import libros, prestamos, usuarios
from .seed import cargar_datos_iniciales


@asynccontextmanager
async def al_iniciar(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # crea las tablas si no existen
    with SessionLocal() as db:
        cargar_datos_iniciales(db)
    yield


app = FastAPI(title="BiblioUMG API",
              description="Sistema de préstamos de biblioteca", version="1.0.0",
              lifespan=al_iniciar)

# CORS: permite que el frontend (otro dominio) llame a esta API.
origenes = os.getenv("FRONTEND_URL", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origenes,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(usuarios.router)
app.include_router(libros.router)
app.include_router(prestamos.router)


@app.get("/salud", tags=["Sistema"])
def salud():
    """Verifica que la API esté funcionando."""
    return {"estado": "ok"}
