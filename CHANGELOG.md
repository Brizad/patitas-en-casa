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
- DT-05 (#30): los cupos del refugio y los animales ingresados se guardan en PostgreSQL (migración `0002`, que crea el refugio demo de 40 cupos). El cupo se toma con un `UPDATE` condicional, seguro aunque haya varios procesos (100 pruebas).
- Detección de secretos en el CI con gitleaks v8.30.1 sobre todo el historial, con una auto-prueba que confirma que un token falso sí se detecta (#33).
- DT-02, parte 1 (#35): cuentas de personal (veterinario, coordinador) con contraseñas Argon2id, tabla `usuarios` (migración `0003`) y comando `python -m app.usuarios.crear_usuario` (130 pruebas).
- DT-02, parte 2 (#37): inicio de sesión del personal con `POST /auth/token` (JWT HS256, 30 minutos) y `GET /auth/yo`. La clave de firma sale de `PATITAS_JWT_SECRETO` (149 pruebas).
- DT-03 (#12): la alerta de ocupación del 90 % (RN-04) se envía por correo SMTP a los coordinadores (`PATITAS_CORREOS_COORDINADORES`); sin SMTP configurado queda en el log. Una falla del correo no deshace el ingreso (167 pruebas).
- DT-06 (#41): `POST /auth/token` limita los intentos fallidos: 5 por correo o 20 por IP en 15 minutos; después responde 429 con `Retry-After`, incluso con la contraseña correcta. Los fallos se guardan en PostgreSQL (tabla `intentos_fallidos`, migración `0004`) y un inicio correcto reinicia el contador del correo (190 pruebas).
- HU-02 (#2): el veterinario confirma la prioridad sugerida o la ajusta con justificación de 10 caracteres o más (`POST /reportes/{codigo}/confirmacion`, RN-06, RN-16). La decisión queda en la bitácora `decisiones_triaje` (migración `0005`, `GET /reportes/{codigo}/decisiones`) y la base también exige la justificación (225 pruebas).
### Cambiado
- `GET /cola` muestra solo los reportes pendientes de confirmar; los confirmados salen de la cola, como en el prototipo (HU-02, #2).
- **Incompatible:** `POST /refugio/ingresos` queda solo para el rol coordinador; un veterinario con sesión recibe 403 y el cupo no cambia. Así lo indica la pantalla P-06 "Registrar ingreso" del prototipo (#45). `GET /cola` y `GET /refugio/ocupacion` siguen para ambos roles (195 pruebas).
- **Incompatible:** `GET /cola`, `POST /refugio/ingresos` y `GET /refugio/ocupacion` exigen el encabezado `Authorization: Bearer <token>` de una cuenta de personal (401 sin sesión, 403 sin permiso). Se elimina `X-Rol` (DT-02, #40).
- La API se inicia con `uvicorn --factory app.api.main:crear_app`; `crear_app()` recibe el repositorio (las pruebas inyectan el de memoria) y el módulo ya no crea la app al importarse (#29).
### Deuda técnica
- DT-01 pagada (#10). DT-05 registrada y pagada (#30). DT-02 pagada (#11). DT-03 pagada (#12). Registrada y pagada DT-06 (#41): límite de intentos de inicio de sesión.

## [0.1.0] - 2026-09-29
### Agregado
- Registro de reportes de emergencia sin cuenta, con validaciones (RF-01, HU-01).
- Triaje por texto con clasificador de reglas v0, política de baja confianza y falla segura (RF-02, RNF-03).
- Cola priorizada con control de rol (RF-04, HU-02).
- Registro de ingresos, control de cupos y alerta al 90 % (RF-06, RF-07, HU-03).
- API REST con FastAPI y pipeline de CI (build, lint, test).
### Corregido
- BUG-01: señales con tilde no se detectaban en el triaje.
