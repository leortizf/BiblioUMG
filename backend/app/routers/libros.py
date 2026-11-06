"""
Rutas del catálogo de libros.
Cualquiera puede consultar; solo el bibliotecario crea, edita o elimina.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import reglas
from ..database import get_db
from ..models import Libro, Prestamo
from ..schemas import LibroIn, LibroOut
from ..security import solo_bibliotecario

router = APIRouter(prefix="/libros", tags=["Libros"])

RUTA_LIBRO = "/{libro_id}"
NO_ENCONTRADO = "Libro no encontrado."


@router.get("", response_model=list[LibroOut])
def buscar_libros(q: str = "", db: Session = Depends(get_db)):
    """Lista libros. Con ?q=texto busca por título, autor o ISBN."""
    consulta = select(Libro).order_by(Libro.titulo)
    if q:
        patron = f"%{q.strip()}%"
        consulta = consulta.where(or_(Libro.titulo.ilike(patron),
                                      Libro.autor.ilike(patron),
                                      Libro.isbn.ilike(patron)))
    return db.scalars(consulta).all()


@router.get(RUTA_LIBRO, response_model=LibroOut)
def obtener_libro(libro_id: int, db: Session = Depends(get_db)):
    libro = db.get(Libro, libro_id)
    if libro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    return libro


@router.post("", response_model=LibroOut, status_code=201)
def crear_libro(datos: LibroIn, db: Session = Depends(get_db), _=Depends(solo_bibliotecario)):
    if db.scalar(select(Libro).where(Libro.isbn == datos.isbn)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un libro con ese ISBN.")
    libro = Libro(**datos.model_dump(), ejemplares_disponibles=datos.ejemplares_totales)
    db.add(libro)
    db.commit()
    db.refresh(libro)
    return libro


@router.put(RUTA_LIBRO, response_model=LibroOut)
def editar_libro(libro_id: int, datos: LibroIn, db: Session = Depends(get_db),
                 _=Depends(solo_bibliotecario)):
    libro = db.get(Libro, libro_id)
    if libro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    otro = db.scalar(select(Libro).where(Libro.isbn == datos.isbn, Libro.id != libro_id))
    if otro:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe otro libro con ese ISBN.")
    prestados = libro.ejemplares_totales - libro.ejemplares_disponibles
    if datos.ejemplares_totales < prestados:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Hay {prestados} ejemplares prestados; no puede reducir a menos.")
    libro.isbn = datos.isbn
    libro.titulo = datos.titulo
    libro.autor = datos.autor
    libro.anio = datos.anio
    libro.ejemplares_totales = datos.ejemplares_totales
    libro.ejemplares_disponibles = datos.ejemplares_totales - prestados
    db.commit()
    db.refresh(libro)
    return libro


@router.delete(RUTA_LIBRO, status_code=204)
def eliminar_libro(libro_id: int, db: Session = Depends(get_db), _=Depends(solo_bibliotecario)):
    libro = db.get(Libro, libro_id)
    if libro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    vigentes = db.scalar(select(func.count()).select_from(Prestamo).where(
        Prestamo.libro_id == libro_id, Prestamo.estado.in_(reglas.ESTADOS_VIGENTES)))
    if vigentes:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "No se puede eliminar un libro con préstamos vigentes.")
    historial = db.scalar(select(func.count()).select_from(Prestamo).where(
        Prestamo.libro_id == libro_id))
    if historial:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "No se puede eliminar un libro con historial de préstamos.")
    db.delete(libro)
    db.commit()
