# CLAUDE.md — Patitas en Casa

Contexto para asistentes de código que trabajen en este repositorio.

## Proyecto

API en FastAPI para la gestión logística de refugios animales en Cúcuta (Norte de Santander):
reporte ciudadano de emergencias sin cuenta, triaje asistido por IA, cola priorizada para
veterinarios y control de cupos del refugio.

- Proyecto integrador de Ingeniería de Software II (grupo CR), Universidad de Pamplona.
- Autor: Brayan David Amado Ramírez. Repositorio: https://github.com/Brizad/patitas-en-casa
- Versión publicada: v0.1.0. En curso: **Incremento 2 — "Fundación segura"**.
- Idioma: todo (código, pruebas, commits, documentación) en **español**.

## Estructura

| Ruta | Contenido |
|------|-----------|
| `app/dominio/modelos.py` | Entidades: `Reporte`, `Ubicacion`, `Animal`, `Refugio`, enums `Prioridad`, `EstadoReporte`, `Especie`. |
| `app/reportes/` | `RepositorioReportes` (Protocol), `RepositorioEnMemoria`, `RepositorioPostgres` y `ServicioReportes` (RF-01). |
| `app/ajustes.py` | Conexión a PostgreSQL leída del entorno o `.env` (`AjustesBD`). |
| `app/bd/` | Tablas (`esquema.py`) y aplicar/verificar migraciones desde Python (`migraciones.py`). |
| `migraciones/` | Alembic: una revisión por cada cambio de `app/bd/esquema.py`. |
| `app/triaje/` | Normalización de texto, clasificador por reglas v0 y `ServicioTriaje` (política RN-02/RN-03). |
| `app/cupos/` | `ServicioCupos` (ingresos, cupos y alerta, RF-06/RF-07) sobre `RepositorioCupos`: en memoria o en PostgreSQL con `UPDATE` condicional (DT-05). |
| `app/api/main.py` | `crear_app(repositorio=None, repositorio_cupos=None)`: endpoints REST; sin argumentos usa PostgreSQL. |
| `app/config.py` | Parámetros de negocio (umbral de confianza, alerta, límites del video). |
| `tests/` | Pruebas pytest (unitarias y de caja negra de la API). |
| `docs/prototipo/` | Prototipo interactivo HTML (no es parte de la API). |

## Reglas de negocio vigentes (no romper)

- **RN-01**: el reporte exige descripción de 20 caracteres o más y ubicación (GPS o dirección);
  video opcional de máximo 60 s y 50 MB.
- **RN-02**: confianza < 0,6 con prioridad media o baja ⇒ estado "requiere revisión"
  (nunca se asigna baja o media automática con baja confianza). Crítica y alta no se degradan.
- **RN-03**: si el clasificador falla o no responde en 10 s ⇒ falla segura: prioridad alta,
  estado "sin clasificar", revisión manual.
- **RN-04**: alerta a coordinadores al llegar al 90 % de ocupación; sin cupo, el ingreso se
  rechaza (409).

Toda prueba existente debe seguir pasando. Si una regla de negocio cambia, se acuerda antes
con el autor.

## Comandos

```bash
pip install -r requirements-dev.txt
ruff check .
alembic upgrade head                   # base patitas
pytest --cov=app                       # PATITAS_EXIGIR_POSTGRES=1 para no omitir las de base
uvicorn --factory app.api.main:crear_app --reload
```

Las pruebas con base usan el marcador `postgres` y la fixture `bd_limpia` de `tests/conftest.py`;
las pruebas de API sin base inyectan `RepositorioEnMemoria` en `crear_app()`.

El CI (`.github/workflows/ci.yml`, job `build-lint-test`) ejecuta Ruff y pytest con cobertura
mínima del 70 %.

## Base de datos (Incremento 2, DT-01)

- PostgreSQL 17 instalado en Windows (sin Docker), `localhost:5432`, usuario `postgres`.
- Base de la aplicación: `patitas`. Base de las pruebas: `patitas_test` (las pruebas pueden
  borrar datos: nunca apuntarlas a `patitas`).
- Credenciales en `.env` (copiar de `.env.example`). La contraseña la escribe el autor; el
  asistente no la lee, no la escribe ni la imprime.
- En el CI la contraseña del contenedor Postgres viene del secret `POSTGRES_TEST_PASSWORD`.

## Reglas de trabajo

1. **Cada cambio sigue el flujo**: issue en GitHub → rama propia desde `main`
   (`feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`) → **pruebas primero** →
   Pull Request que referencia el issue, con CI en verde.
2. **Merges:** el asistente puede integrar un PR (`gh pr merge --squash --delete-branch`) solo
   con el CI en verde y sin `.env`, contraseñas reales ni tokens en el diff (las contraseñas
   falsas en pruebas están permitidas). Después de cada merge, resume en 2 líneas qué cambió y
   por qué. Nunca hace push directo a `main`.
3. **Nunca subir contraseñas, tokens ni el archivo `.env`.** Las credenciales se leen de
   variables de entorno / `.env` (ignorado por git). En el repositorio solo va `.env.example`
   con valores de ejemplo.
4. Mantener RN-01 a RN-04 y que pasen todas las pruebas.
5. Cambios pequeños: un PR por paso del plan.
6. Explicar en español sencillo qué se hace y por qué: el autor debe sustentarlo.
7. Registrar cambios en `CHANGELOG.md` (Keep a Changelog, SemVer) y actualizar
   `DEUDA_TECNICA.md` cuando se pague o se cree deuda.

## Deuda técnica abierta

Ver `DEUDA_TECNICA.md`: DT-02 (rol en encabezado `X-Rol` → OAuth2/JWT + Argon2id), DT-03
(notificaciones en consola) y DT-04 (clasificador por reglas → modelo Transformer). Pagadas:
DT-01 (reportes en PostgreSQL) y DT-05 (cupos en PostgreSQL).
