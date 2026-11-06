# BiblioUMG — Sistema de préstamos de biblioteca

Aplicación web cliente-servidor para gestionar el préstamo de libros de una biblioteca universitaria. Es el objeto de evaluación del proyecto final del curso Aseguramiento de la Calidad de Software (UMG, 2026).

> **Origen:** aplicación generada con inteligencia artificial (Claude, de Anthropic) a partir de la especificación del archivo `SPEC.md`. Ver sección 2.3 del enunciado.

## Estructura

```
biblioteca/
├── backend/            API REST (Python + FastAPI)
│   ├── app/
│   │   ├── main.py         punto de entrada
│   │   ├── reglas.py       reglas de negocio (módulo crítico)
│   │   ├── models.py       tablas de la base de datos
│   │   ├── schemas.py      validación de datos de entrada/salida
│   │   ├── security.py     contraseñas y tokens (JWT)
│   │   ├── seed.py         datos iniciales de ejemplo
│   │   └── routers/        endpoints: usuarios, libros, préstamos
│   └── requirements.txt
├── frontend/           Sitio web (JavaScript + Vite)
│   ├── src/
│   │   ├── main.js         pantallas
│   │   ├── api.js          comunicación con la API
│   │   └── validaciones.js validaciones y formato
│   └── package.json
├── render.yaml         plano de despliegue en Render
└── SPEC.md             especificación con la que se generó la aplicación
```

## Requisitos

Git, Python 3.12, Node.js 20 LTS o superior. No se necesita Docker.

## Ejecución local

**Backend** (terminal 1):

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API queda en http://localhost:8000 y su documentación interactiva en http://localhost:8000/docs. En local usa SQLite (archivo `biblioteca.db`); para empezar de cero basta con borrar ese archivo.

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

El sitio queda en http://localhost:5173.

## Cuentas de prueba

| Rol | Correo | Contraseña |
|---|---|---|
| Bibliotecario | admin@biblioumg.com | Admin12345 |
| Estudiante | estudiante@biblioumg.com | Estudiante123 |
| Docente | docente@biblioumg.com | Docente123 |

## Reglas de negocio

| Tipo | Préstamos simultáneos | Días de préstamo | Renovaciones | Multa por día |
|---|---|---|---|---|
| Estudiante | 3 | 7 | 1 | Q2.00 |
| Docente | 5 | 14 | 2 | Q1.00 |

Desde el octavo día de atraso la tarifa diaria se duplica; la multa de un préstamo tiene un tope de Q50.00; un atraso mayor a 30 días bloquea al usuario; con multa pendiente o bloqueo no se puede solicitar ni renovar. Estados del préstamo: Solicitado, Activo, Renovado, Vencido, Devuelto, Rechazado y Cancelado.

## Pruebas

**Línea base (registrada en la fase 1):** el proyecto de origen no incluía pruebas automatizadas (0 pruebas, 0 % de cobertura).

**Pruebas unitarias del backend (pytest):**

```bash
cd backend
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term
```

**Pruebas unitarias del frontend (Vitest):**

```bash
cd frontend
npm install
npm test            # solo pruebas
npm run coverage    # pruebas con cobertura
```

**Pruebas de API (Postman / Newman),** con la API encendida en local:

```bash
npx newman run postman/BiblioUMG.postman_collection.json -e postman/local.postman_environment.json
```

La colección también se puede importar en Postman (Import → los dos archivos de la carpeta `postman`).

**Prueba de carga (k6):** en GitHub, pestaña **Actions → Prueba de carga k6 → Run workflow**. El script está en `carga/carga.js`.

## Pipeline CI/CD

El archivo `.github/workflows/pipeline.yml` ejecuta en GitHub Actions, en orden: compilación, pruebas unitarias, análisis estático con SonarCloud (quality gate), pruebas de API con Newman y despliegue a Render. Se ejecuta en cada push y Pull Request hacia `dev`, `qa` y `main`; el despliegue solo ocurre en push a `qa` o `main`.

Secretos requeridos en **Settings → Secrets and variables → Actions**: `SONAR_TOKEN`, `RENDER_DEPLOY_HOOK_API` y `RENDER_DEPLOY_HOOK_WEB`. La estrategia de ramas está en `docs/ESTRATEGIA_RAMAS.md`.

## Despliegue en la nube (capa gratuita)

1. Crear una base de datos gratuita en [Neon](https://neon.tech) y copiar su cadena de conexión (empieza con `postgresql://`).
2. En [Render](https://render.com), elegir **New → Blueprint**, conectar este repositorio y confirmar. Render leerá `render.yaml` y creará dos servicios.
3. Completar las variables que Render solicita:
   - `biblioumg-api` → `DATABASE_URL`: la cadena de Neon. `FRONTEND_URL`: la URL del sitio web.
   - `biblioumg-web` → `VITE_API_URL`: la URL de la API.
4. Cuando cambie una variable del sitio web, volver a desplegarlo (Manual Deploy), porque la URL de la API se incrusta al compilar.

Nota: los servicios gratuitos de Render se suspenden tras 15 minutos sin uso; la primera petición después de eso puede tardar hasta un minuto.
