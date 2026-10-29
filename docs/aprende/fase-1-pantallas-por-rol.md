# Fase 1 · Pantallas por rol (RF-13 a RF-16, RF-21, RF-22)

Issue #67. PR apilados: #68 → #69 → #70 → #71 → #72 → #73 → este.

## Qué hace

- **Administrador** (rol nuevo): crea cuentas, las suspende o reactiva, registra refugios y
  vincula a cada persona con su refugio.
- **Primer administrador sin consola**: si existen `PATITAS_ADMIN_CORREO` y
  `PATITAS_ADMIN_CONTRASENA`, la cuenta se crea al arrancar la API.
- **Panel por rol**: al iniciar sesión cada persona ve solo sus pantallas:
  veterinario → cola; coordinador → refugio (ocupación e ingresos); rescatista → mis
  rescates; administrador → administración.

## Por qué se hizo así

1. **Administrador por variables de entorno.** En el plan gratis de Render no hay consola
   para ejecutar `python -m app.usuarios.crear_usuario`. Sin una primera cuenta nadie podría
   crear las demás. La cuenta se crea **solo si no existe**: Render reinicia el servicio a
   menudo y no queremos pisar una contraseña que el administrador ya cambió. La contraseña
   vive en los secretos de Render, nunca en el repositorio, y nunca se escribe en el log.
2. **Suspender sin esperar a que venza el token.** El JWT dura 30 minutos, pero la
   dependencia `usuario_actual` (en `app/api/seguridad.py`) vuelve a leer la cuenta en cada
   petición: si está suspendida responde 401 de inmediato. Por eso no hace falta una «lista
   negra» de tokens.
3. **Nadie se suspende a sí mismo** (409): así no se pierde la última cuenta de
   administración por un clic.
4. **El panel oculta, el servidor decide.** `pantallasDelRol()` (en `panel/src/navegacion.ts`)
   solo evita mostrar botones que siempre fallarían. La seguridad real son las dependencias
   `exigir_rol(...)` del servidor (401 sin sesión, 403 con otro rol). Ocultar un botón no es
   seguridad: cualquiera puede llamar a la API con `curl`.
5. **El refugio guarda su lista de personal en la cuenta** (`usuarios.refugio_id`, opcional).
   Una columna con llave foránea basta: una persona trabaja en un solo refugio.
6. **Mensajes honestos (lección D-05):** la pantalla del refugio dice «ocupación en nivel de
   alerta», no «se avisó a coordinación», porque la pantalla no sabe si el correo llegó.

## Recorrido de una petición: suspender una cuenta

1. En el panel, el administrador pulsa «Suspender» (`Administracion.tsx`).
2. `cambiarActivo()` (`apiAdmin.ts`) envía `PUT /admin/usuarios/vet@x.co/activo` con
   `{"activo": false}` y el encabezado `Authorization: Bearer <token>`.
3. FastAPI ejecuta la dependencia `administracion = exigir_rol(..., Rol.ADMINISTRADOR)`:
   valida el token, relee la cuenta y comprueba el rol.
4. El endpoint `suspender_o_reactivar` (en `app/api/main.py`) llama a
   `ServicioUsuarios.cambiar_activo()`, que impide la auto-suspensión y pide al repositorio
   `cambiar_activo()`.
5. `RepositorioUsuariosPostgres` ejecuta `UPDATE usuarios SET activo = false WHERE correo = ...`
   y devuelve si cambió una fila (si no, 404).
6. La siguiente petición de esa veterinaria llega con su token todavía vigente, pero
   `usuario_actual` ve `activo = false` y responde 401.

## Archivos a leer, en orden

1. `app/usuarios/admin_inicial.py` y su prueba `tests/test_admin_inicial.py`.
2. `migraciones/versions/0010_rol_administrador.py` y `0011_personal_vinculado_a_refugio.py`.
3. `app/usuarios/servicio.py` (`listar`, `cambiar_activo`) y `app/usuarios/repositorio*.py`.
4. `app/refugios/` (repositorio en memoria y en PostgreSQL).
5. En `app/api/main.py`, la sección «Fase 1 (#67)».
6. `tests/test_admin_cuentas.py` y `tests/test_admin_refugios.py`.
7. `panel/src/navegacion.ts`, `App.tsx`, `Rescatista.tsx`, `Refugio.tsx`, `Administracion.tsx`.

## Cómo probarlo

```bash
pytest tests/test_admin_inicial.py tests/test_admin_cuentas.py tests/test_admin_refugios.py -q
cd panel && npm test
```

A mano: pon `PATITAS_ADMIN_CORREO` y `PATITAS_ADMIN_CONTRASENA` en tu `.env`, ejecuta
`alembic upgrade head` y `uvicorn --factory app.api.main:crear_app`, compila el panel
(`cd panel && npm run build`) y entra a `http://127.0.0.1:8000/panel/` con esa cuenta.
Crea un rescatista, entra con él, márcate disponible y acepta una oferta.

En Render: *Environment* → agrega las dos variables y reinicia el servicio.

## Preguntas de práctica para la sustentación

1. ¿Por qué el administrador inicial no reemplaza la cuenta si ya existe? ¿Qué pasaría si lo
   hiciera y Render reiniciara el servicio?
2. Si el JWT dura 30 minutos, ¿cómo logra el sistema que una cuenta suspendida pierda el
   acceso en la siguiente petición?
3. Ocultar la pantalla «Administración» a un veterinario, ¿lo protege de llamar a
   `POST /admin/usuarios`? ¿Qué lo protege de verdad?
4. ¿Por qué `crear_admin_inicial` registra en el log la regla incumplida pero no la
   contraseña? ¿Qué ley y qué requisito no funcional se relacionan con eso?
5. ¿Por qué la migración `0010` puede fallar al hacer `downgrade` si hay administradores, y
   por qué eso es preferible a borrar las cuentas?
