# Especificación de generación de la aplicación

Documento requerido por la sección 2.3 del enunciado (aplicaciones generadas con IA).

- **Herramienta:** Claude (Anthropic), en claude.ai.
- **Fecha de generación:** 23 de septiembre de 2026.
- **Forma de uso:** conversación en la que se solicitó una aplicación web cliente-servidor, con backend en Python, de dominio "préstamos de biblioteca", con reglas de negocio suficientes para aplicar partición de equivalencia, valores límite, tablas de decisión y transición de estados. Se adjunta además la transcripción o capturas de los prompts de esa conversación.

## Especificación funcional solicitada

1. Usuarios de tipo estudiante o docente que se registran con nombre, carné (formato 0000-00-000 a 0000-00-000000), correo y contraseña (8 a 64 caracteres). Un rol bibliotecario administra el sistema.
2. Catálogo de libros con ISBN-13 validado por dígito verificador, título, autor, año (1450 al año actual) y ejemplares (1 a 20). Búsqueda por título, autor o ISBN.
3. Préstamos con ciclo de vida: Solicitado → Activo → Renovado → Vencido → Devuelto, más Rechazado y Cancelado como estados finales. Transiciones no permitidas se rechazan.
4. Límites por tipo: estudiante 3 préstamos, 7 días, 1 renovación, Q2.00 diarios; docente 5 préstamos, 14 días, 2 renovaciones, Q1.00 diarios.
5. Multa: tarifa normal los primeros 7 días de atraso, tarifa doble desde el día 8, tope de Q50.00 por préstamo.
6. Bloqueo del usuario si devuelve con más de 30 días de atraso. Con multa pendiente o bloqueo no puede solicitar ni renovar. Para desbloquear debe haber pagado la multa completa.
7. El bibliotecario puede registrar entregas y devoluciones con fecha pasada (máximo 60 días atrás, nunca futura).
8. Pagos de multa parciales o totales; el monto no puede exceder la deuda.

## Especificación técnica solicitada

- Backend: Python 3.12, FastAPI, SQLAlchemy, autenticación con JWT.
- Base de datos: SQLite en local, PostgreSQL (Neon) en la nube.
- Frontend: JavaScript con Vite, separado del backend y con su propio proceso de construcción.
- Despliegue en capa gratuita: Render (API y sitio estático) + Neon (base de datos).
- Sin pruebas automatizadas incluidas (línea base cero).
