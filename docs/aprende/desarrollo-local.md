# Desarrollo local en Windows

Mientras Neon está suspendido (y en general, para no gastar sus horas), el sistema completo corre
en tu PC: API + PWA + panel + PostgreSQL 17 local. Un solo comando lo deja listo:
`scripts/dev/arrancar_local.ps1`.

## Lo que necesitas (una sola vez)

- **PostgreSQL 17** encendido (servicio `postgresql-x64-17`) con la base `patitas` creada.
  Si no existe: `& "C:\Program Files\PostgreSQL\17\bin\createdb.exe" -U postgres patitas`.
- **Python 3.12** (`py -3.12 --version`) y **Node.js 22 o más nuevo** (`node --version`).
- Un archivo **`.env`** en la raíz del repositorio. Créalo desde el ejemplo y complétalo tú (el
  asistente nunca lo lee ni lo escribe):

  ```powershell
  Copy-Item .env.example .env
  notepad .env
  ```

  | Variable | Qué poner |
  |---|---|
  | `POSTGRES_PASSWORD` | La contraseña de tu usuario `postgres` local |
  | `POSTGRES_DB` | `patitas` |
  | `PATITAS_JWT_SECRETO` | `python -c "import secrets; print(secrets.token_hex(32))"` |
  | `PATITAS_CLAVE_DATOS` | Otra generada igual (si falta, el reporte no acepta contacto) |
  | `PATITAS_DEMO_CONTRASENA` | 12 caracteres o más: es la de **todas** las cuentas de demostración |

## Arrancar

Desde la raíz del repositorio, en PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\arrancar_local.ps1
```

El script, en orden: revisa `.env` (si falta, dice qué copiar), prepara `.venv` si no existe,
aplica `alembic upgrade head`, compila el panel (`npm ci` y `npm run build` en `panel/`), activa
los datos de demostración y arranca `uvicorn --factory app.api.main:crear_app --reload --port 8000`.
Se detiene con **Ctrl+C**.

Opciones: `-SinPanel` (no recompila el panel: arranca en segundos), `-Puerto 8001`,
`-SinRecarga` (sin `--reload`).

## Qué abro en el navegador

| Dirección | Qué es | Quién la usa |
|---|---|---|
| <http://localhost:8000/> | Página de inicio pública | Cualquiera |
| <http://localhost:8000/app/> | PWA ciudadana: reportar sin cuenta y seguir el caso con el código | Ciudadano |
| <http://localhost:8000/panel/> | Panel del personal (iniciar sesión) | Personal y adoptante |
| <http://localhost:8000/docs> | API (Swagger) | Desarrollo |

## Con qué cuentas entro al panel

Todas usan la contraseña que pusiste en `PATITAS_DEMO_CONTRASENA`:

| Correo | Rol | Qué ve |
|---|---|---|
| `veterinaria@demo.patitas.co` | Veterinario | Cola priorizada, confirmar o ajustar la prioridad (RN-06/RN-16), descartar, historial clínico |
| `coordinador@demo.patitas.co` | Coordinador | Ocupación y cupos (RN-04), ingresos al refugio, adopciones, indicadores |
| `rescatista@demo.patitas.co` | Rescatista | Rescates ofrecidos de su zona, aceptar, llegué, resultado (RN-08) |
| `adoptante@demo.patitas.co` | Adoptante | Animales publicados y sus solicitudes de adopción |
| `admin@demo.patitas.co` | Administrador | Cuentas del personal, refugios, piloto |
| `alcaldia@demo.patitas.co` | Alcaldía | Solo indicadores anonimizados |

Los datos de demostración (reportes en varias comunas, un crítico esperando rescatista, animales
en el refugio y tres en adopción) se cargan **una sola vez**: si la cuenta de la veterinaria ya
existe, no se repiten. Para empezar de cero, borra y crea la base:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\dropdb.exe" -U postgres patitas
& "C:\Program Files\PostgreSQL\17\bin\createdb.exe" -U postgres patitas
```

## Cuando algo falla

| Mensaje del script | Qué hacer |
|---|---|
| «No existe .env» | Sigue la tabla de arriba |
| «Faltan en .env: …» | Completa esas variables (el script nunca muestra sus valores) |
| «Falló: alembic upgrade head» | ¿Está encendido el servicio de PostgreSQL? ¿Existe la base `patitas`? ¿La contraseña es la correcta? |
| «Falló: npm ci» | Instala Node.js 22 o más nuevo |

Sin SMTP configurado, los avisos (al rescatista, al ciudadano) se escriben en la consola de
uvicorn como «Notificación para …»: así ves que salieron sin mandar correos reales.

## Cómo se probó (24-nov)

En un PC sin `.env` el script se detiene en el paso 1 con las instrucciones de arriba. El
recorrido completo se probó contra un PostgreSQL 17 temporal (otro puerto, datos falsos) con
`-ArchivoEnv`: migraciones, `npm ci`, compilación del panel, datos de demostración y uvicorn; `/`,
`/app/`, `/panel/` y `/docs` respondieron 200 y las seis cuentas iniciaron sesión.
