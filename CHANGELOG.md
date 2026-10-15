# Cambios

Formato basado en *Keep a Changelog*; versiones según SemVer.

## [Sin publicar]
### Corregido
- BUG-02 (#16): la negación se detectaba por subcadena ("vecino", "camino", "pequeño") y degradaba casos críticos; ahora se compara la palabra anterior en cada aparición de la señal.
- BUG-03 (#17): dos clasificaciones colgadas agotaban el pool del triaje; al agotarse el tiempo se descarta el ejecutor y el error queda registrado con logging.
- BUG-04 (#18): dos ingresos simultáneos podían superar la capacidad del refugio; el cupo se comprueba y ocupa bajo un candado y `Refugio` valida 0 ≤ ocupados ≤ capacidad.
### Agregado
- Prueba del tiempo agotado del triaje (PA-02) y pruebas de regresión de BUG-02, BUG-03 y BUG-04 (40 pruebas, 97 % de cobertura).
- `CLAUDE.md` con el contexto del proyecto y las reglas de trabajo del incremento 2, y `.env.example` con las variables de PostgreSQL sin valores reales (#21).
- DT-01, paso 1 (#23): `app/ajustes.py` lee la conexión a PostgreSQL desde el entorno o `.env`; la contraseña no se imprime y, si falta, el error indica cómo completar el `.env`.
- DT-01, paso 2 (#25): pruebas de contrato de `RepositorioReportes`, parametrizadas por implementación (52 pruebas).
- DT-01, paso 3 (#27): `RepositorioPostgres` con SQLAlchemy y psycopg, tabla `reportes` creada por la migración de Alembic `0001` y CI con un servicio PostgreSQL 17 (79 pruebas).
- DT-01, paso 4 (#29): la API usa PostgreSQL al ejecutarse; los reportes sobreviven a un reinicio. Al arrancar se comprueba que la base esté en la última migración (83 pruebas).
### Cambiado
- La API se inicia con `uvicorn --factory app.api.main:crear_app`; `crear_app()` recibe el repositorio (las pruebas inyectan el de memoria) y el módulo ya no crea la app al importarse (#29).
### Deuda técnica
- DT-01 pagada (#10). Registrada DT-05 (#30): los cupos del refugio siguen en memoria.

## [0.1.0] - 2026-09-29
### Agregado
- Registro de reportes de emergencia sin cuenta, con validaciones (RF-01, HU-01).
- Triaje por texto con clasificador de reglas v0, política de baja confianza y falla segura (RF-02, RNF-03).
- Cola priorizada con control de rol (RF-04, HU-02).
- Registro de ingresos, control de cupos y alerta al 90 % (RF-06, RF-07, HU-03).
- API REST con FastAPI y pipeline de CI (build, lint, test).
### Corregido
- BUG-01: señales con tilde no se detectaban en el triaje.
