"""
Datos iniciales: se cargan automáticamente la primera vez que arranca el sistema
(solo si la tabla de usuarios está vacía).

Cuentas de prueba (las contraseñas se pueden cambiar con variables de entorno):
  Bibliotecario: admin@biblioumg.com    / Admin12345
  Estudiante:    estudiante@biblioumg.com / Estudiante123
  Docente:       docente@biblioumg.com    / Docente123
"""
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Libro, Usuario
from .security import hashear_password

LIBROS = [
    ("9785260181591", "Fundamentos de ingeniería de software", "Laura Méndez", 2019, 3),
    ("9780830166138", "Pruebas de software en la práctica", "Carlos Ajú", 2021, 2),
    ("9781860913907", "Estructuras de datos con Python", "Ana Lucía Pérez", 2020, 4),
    ("9789960308241", "Bases de datos relacionales", "Jorge Castillo", 2018, 2),
    ("9786281948217", "Redes de computadoras", "María José Solís", 2017, 1),
    ("9789935181909", "Arquitectura de software moderna", "Diego Ramírez", 2022, 2),
    ("9789378657979", "Historia de Guatemala", "Rosa Tzul", 2015, 5),
    ("9785432319487", "Cálculo diferencial", "Pedro Morales", 2016, 3),
    ("9787574911864", "Álgebra lineal aplicada", "Sofía Herrera", 2014, 2),
    ("9782527601892", "Ética profesional en ingeniería", "Luis Barrios", 2023, 1),
    ("9785559797113", "Sistemas operativos", "Andrea Quiñónez", 2019, 2),
    ("9784710497466", "Inteligencia artificial: una introducción", "Marco Estrada", 2024, 3),
]


def cargar_datos_iniciales(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Usuario)):
        return  # ya hay datos; no se hace nada

    cuentas = [
        ("Bibliotecaria General", "0000-00-00001", os.getenv("ADMIN_EMAIL", "admin@biblioumg.com"),
         os.getenv("ADMIN_PASSWORD", "Admin12345"), "DOCENTE", "BIBLIOTECARIO"),
        ("Estudiante de Prueba", "0901-22-10001", "estudiante@biblioumg.com",
         os.getenv("DEMO_PASSWORD_ESTUDIANTE", "Estudiante123"), "ESTUDIANTE", "USUARIO"),
        ("Docente de Prueba", "0901-10-20001", "docente@biblioumg.com",
         os.getenv("DEMO_PASSWORD_DOCENTE", "Docente123"), "DOCENTE", "USUARIO"),
    ]
    for nombre, carne, email, password, tipo, rol in cuentas:
        db.add(Usuario(nombre=nombre, carne=carne, email=email,
                       password_hash=hashear_password(password), tipo=tipo, rol=rol))

    for isbn, titulo, autor, anio, ejemplares in LIBROS:
        db.add(Libro(isbn=isbn, titulo=titulo, autor=autor, anio=anio,
                     ejemplares_totales=ejemplares, ejemplares_disponibles=ejemplares))
    db.commit()
