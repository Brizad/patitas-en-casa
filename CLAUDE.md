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
| `app/usuarios/` | Cuentas del personal (DT-02): contraseñas Argon2id, `ServicioUsuarios`, repositorios y comando `crear_usuario`. |
| `app/seguridad/tokens.py`, `app/api/seguridad.py` | Tokens JWT (`EmisorTokens`) y la dependencia de FastAPI que exige sesión. |
| `app/notificaciones/correo.py` | Adaptadores de `Notificador` (DT-03): correo SMTP o, sin SMTP configurado, el log. |
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
las pruebas de API sin base inyectan repositorios en memoria y un `EmisorTokens` con clave falsa
en `crear_app()`, y obtienen el token con `POST /auth/token` (ver `sesion()` en
`tests/test_api.py`).

## Seguridad (DT-02)

- Públicos: `POST /reportes`, `GET /reportes/{codigo}` (ciudadano sin cuenta, RF-01) y
  `POST /auth/token`. Todo lo demás exige `Authorization: Bearer` de personal
  (`exigir_rol` en `app/api/seguridad.py`). `X-Rol` ya no existe: no reintroducirlo.
- Contraseñas solo como hash Argon2id; nunca registrar contraseñas ni tokens en logs.
- Endpoint nuevo del personal → `dependencies=[personal]` y una prueba de 401 sin sesión.

El CI (`.github/workflows/ci.yml`, job `build-lint-test`) ejecuta gitleaks (secretos en todo el
historial), Ruff y pytest con cobertura mínima del 70 %.

## Base de datos (Incremento 2, DT-01)

- PostgreSQL 17 instalado en Windows (sin Docker), `localhost:5432`, usuario `postgres`.
- Base de la aplicación: `patitas`. Base de las pruebas: `patitas_test` (las pruebas pueden
  borrar datos: nunca apuntarlas a `patitas`).
- Credenciales en `.env` (copiar de `.env.example`). La contraseña la escribe el autor; el
  asistente no la lee, no la escribe ni la imprime.
- En el CI la contraseña del contenedor Postgres viene del secret `POSTGRES_TEST_PASSWORD`.
- `PATITAS_JWT_SECRETO` (clave de firma de los tokens, ≥ 32 caracteres) vive solo en `.env`;
  las pruebas usan una clave falsa propia y no la necesitan.

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

Ver `DEUDA_TECNICA.md`: DT-04 (clasificador por reglas → modelo Transformer) y DT-06 (sin
límite de intentos de inicio de sesión). Pagadas: DT-01 (reportes en PostgreSQL), DT-02 (JWT +
Argon2id), DT-03 (notificador por correo) y DT-05 (cupos en PostgreSQL).
