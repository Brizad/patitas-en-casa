# CLAUDE.md — Patitas en Casa

Contexto para asistentes de código que trabajen en este repositorio.

## Proyecto

API en FastAPI para la gestión logística de refugios animales en Cúcuta (Norte de Santander):
reporte ciudadano de emergencias sin cuenta, triaje asistido por IA, cola priorizada para
veterinarios y control de cupos del refugio.

- Proyecto integrador de Ingeniería de Software II (grupo CR), Universidad de Pamplona.
- Autor: Brayan David Amado Ramírez. Repositorio: https://github.com/Brizad/patitas-en-casa
- Versión publicada: v0.2.0 (incremento 2, "Fundación segura").
- Idioma: todo (código, pruebas, commits, documentación) en **español**.

## Estructura

| Ruta | Contenido |
|------|-----------|
| `app/dominio/modelos.py` | Entidades: `Reporte`, `Ubicacion`, `Animal`, `Refugio`, enums `Prioridad`, `EstadoReporte`, `Especie`. |
| `app/reportes/` | `RepositorioReportes` (Protocol), `RepositorioEnMemoria`, `RepositorioPostgres`, `ServicioReportes` (RF-01) y `ServicioConfirmacion` (HU-02). |
| `app/rescates/` | `ServicioRescates` y repositorios (memoria y PostgreSQL) del rescatista (HU-06, RN-08). |
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
| `app/avisos/` | Outbox de avisos (#63): modelo, repositorios (memoria y PostgreSQL) y `ProcesadorAvisos` (reintentos, estado real). |
| `app/notificaciones/canal.py` | Puerto `CanalAviso` y `EntregaFallida`; el procesador no conoce el SMTP. |
| `panel/` | Panel del personal en React + TypeScript (Vite); se compila a `app/panel_web` (ignorado por git) y se sirve en `/panel/`. |
| `app/pwa/` | PWA ciudadana (HU-08, #47): HTML, CSS y JS sencillos servidos en `/app/` con CSP estricta; sin recursos externos ni `innerHTML` con datos; el service worker solo guarda la interfaz. |
| `docs/aprende/` | Guía de estudio: mapa y glosario, una guía por fase, avance y preguntas para el autor. |
| `docs/prototipo/` | Prototipo interactivo HTML (no es parte de la API; la PWA reutiliza su diseño). |

## Reglas de negocio vigentes (no romper)

- **RN-01**: el reporte exige descripción de 20 caracteres o más y ubicación (GPS o dirección);
  video opcional de máximo 60 s y 50 MB.
- **RN-02**: confianza < 0,6 con prioridad media o baja ⇒ estado "requiere revisión"
  (nunca se asigna baja o media automática con baja confianza). Crítica y alta no se degradan.
- **RN-03**: si el clasificador falla o no responde en 10 s ⇒ falla segura: prioridad alta,
  estado "sin clasificar", revisión manual.
- **RN-04**: alerta a coordinadores al llegar al 90 % de ocupación; sin cupo, el ingreso se
  rechaza (409).
- **RN-06 / RN-16** (HU-02): solo el veterinario confirma la prioridad; ajustarla exige una
  justificación de 10 caracteres o más y queda en la bitácora `decisiones_triaje`. Un reporte
  se confirma una sola vez y sale de la cola.
- **RN-08** (HU-06): un rescate tiene un solo rescatista y un rescatista un solo rescate activo
  (índices únicos parciales en `rescates`). Se ofrecen solo confirmados críticos o altos, a
  rescatistas disponibles. Decisión del autor (#46): zona por comunas de Cúcuta (1 a 10; vacío =
  toda la ciudad; reporte sin comuna = a todos), alerta por correo y escalamiento al coordinador
  sin aceptar a los 15 min (crítico) o 30 min (alto, prototipo): el caso pasa a toda la ciudad.
  Valores en `app/config.py`; el aviso sale una sola vez (tabla `escalamientos`).
- **Avisos (#63)**: confirmar guarda los avisos como pendientes en la misma transacción; el
  envío es del procesador. Nunca decir que un aviso «se envió» o «llegó» si no está `enviado`.
- **RN-14** (HU-08): la consulta por código (`/reportes/{codigo}/seguimiento`) muestra solo el
  código, los pasos y sus fechas; nunca descripción, ubicación, prioridad ni correos.

Fuente de las reglas que no están en el código: `docs/prototipo/interaccion.js` (encabezado y
acciones). Ese prototipo es un entregable calificado: se lee, no se modifica.

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
- `POST /refugio/ingresos` es solo del coordinador (`dependencies=[coordinacion]`, 403 para el
  veterinario; pantalla P-06 del prototipo). `GET /cola` y `GET /refugio/ocupacion` usan `personal`.
- Endpoint nuevo del personal → `dependencies=[personal]` (o `[coordinacion]`) y una prueba de
  401 sin sesión.
- DT-06: `POST /auth/token` cuenta los fallos por correo y por IP (`LimiteIntentos` en
  `app/usuarios/intentos.py`, tabla `intentos_fallidos`); bloqueado responde 429 con `Retry-After`.

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
2. **Merges (desde II-02):** el asistente **no** integra un PR hasta que el autor deje en el PR
   su comentario de revisión con la lista del acuerdo de terminado. Cada PR tiene 300 líneas
   cambiadas o menos (sin contar archivos generados como `package-lock.json`); si un cambio
   necesita más, se parte o se justifica antes de abrirlo. Siempre con el CI en verde y sin
   `.env`, contraseñas reales ni tokens en el diff. Nunca hace push directo a `main`.
3. **Nunca subir contraseñas, tokens ni el archivo `.env`.** Las credenciales se leen de
   variables de entorno / `.env` (ignorado por git). En el repositorio solo va `.env.example`
   con valores de ejemplo.
4. Mantener RN-01 a RN-04 y que pasen todas las pruebas.
5. Cambios pequeños: un PR por paso del plan.
6. Explicar en español sencillo qué se hace y por qué: el autor debe sustentarlo.
7. Registrar cambios en `CHANGELOG.md` (Keep a Changelog, SemVer) y actualizar
   `DEUDA_TECNICA.md` cuando se pague o se cree deuda.

## Deuda técnica abierta

Ver `DEUDA_TECNICA.md`: DT-04 (clasificador por reglas → modelo Transformer). Pagadas: DT-01 (reportes en
PostgreSQL), DT-02 (JWT + Argon2id), DT-03 (notificador por correo), DT-05 (cupos en
PostgreSQL) y DT-06 (límite de intentos de inicio de sesión).
