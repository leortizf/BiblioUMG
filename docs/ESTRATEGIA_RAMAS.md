# Estrategia de ramas y control de cambios (E9)

| Rama | Ambiente | Cómo entran los cambios | Qué ejecuta el pipeline |
|---|---|---|---|
| `feature/<descripcion>` | Trabajo individual | Commits de una integrante | Nada hasta abrir el Pull Request |
| `dev` | Desarrollo (DEV) | Pull Request desde una rama `feature/...`, revisado por la otra integrante | Compilación, pruebas unitarias, SonarCloud y pruebas de API |
| `qa` | Pruebas (QA) | Pull Request desde `dev` | Pipeline completo y despliegue al ambiente `qa` |
| `main` | Producción (PROD) | Pull Request desde `qa` | Pipeline completo y despliegue a Render (ambiente `produccion`) |

## Política de promoción

1. Todo cambio nace en una rama `feature/<descripcion>` creada desde `dev`.
2. Se integra a `dev` mediante Pull Request. La otra integrante revisa el contenido: que las pruebas verifiquen una regla real, que los nombres sean claros y que no se suban secretos. Deja comentarios y aprueba o pide cambios.
3. `dev` se promueve a `qa`, y `qa` a `main`, solo mediante Pull Request.
4. Nadie hace push directo a `qa` ni a `main`.
5. El merge hacia `qa` y `main` está bloqueado si el pipeline falla.

## Reglas de protección configuradas en GitHub (Settings → Rules → Rulesets)

Ruleset `proteccion-qa-main`, aplicado a `qa` y `main`:

- Requerir Pull Request antes de hacer merge.
- Requerir que pasen las verificaciones `1. Compilación`, `2. Pruebas unitarias`, `3. Análisis estático (SonarCloud)` y `4. Pruebas de API (Newman)`.
- Bloquear force push y eliminación de la rama.

## Ambientes de despliegue

Los secretos de despliegue están separados por ambiente de GitHub (Settings → Environments): `produccion` contiene los deploy hooks de los servicios de Render de producción y `qa` los del ambiente de pruebas. Así, un merge a `qa` nunca despliega en producción.
