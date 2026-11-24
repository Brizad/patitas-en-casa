# Despliegue en Render y su verificación

**Cómo se despliega.** Render mira `main` (`render.yaml`, `autoDeploy: true`) y construye la imagen
del `Dockerfile`. Si la construcción o el arranque fallan, **Render deja viva la versión anterior**
y no avisa a nadie: la página sigue respondiendo y parece que todo está bien.

**Por qué existe `deploy.yml`.** El 20-nov-2026 los seis despliegues desde `9a851c2` fallaron (la causa
se ve en el registro de Render, que no se pudo leer desde la sesión de trabajo) y producción siguió en la versión 1.1.0 sin que nadie lo notara. El flujo
`.github/workflows/deploy.yml` (guía 11, trabajo 6b) no despliega nada: después de cada CI en
verde en `main` espera hasta 20 minutos a que `/openapi.json` de producción diga la versión de
`pyproject.toml` y comprueba `/app/` (200) y `/reportes/NOEXISTE` (404). Si no llega, queda en
rojo y GitHub te avisa por correo.

**Lo que NO necesita nada nuevo:** la verificación y el aviso (se activan solos con el próximo CI verde en `main`).

**Lo que falta, y solo tú puedes poner (reversa automática):**

| Secreto | De dónde sale |
|---|---|
| `RENDER_API_KEY` | Render → *Account Settings* → *API Keys* → *Create API Key* |
| `RENDER_SERVICE_ID` | La URL del servicio en Render: `https://dashboard.render.com/web/srv-XXXX…`; el valor es `srv-XXXX…` |

Se guardan en GitHub → *Settings* → *Secrets and variables* → *Actions*. Sin ellos, el trabajo
`revertir` solo deja un aviso amarillo y termina. Con ellos, si la versión nueva **sí** quedó viva
pero `/app/` o `/reportes/…` no responden como deben, el flujo pide a Render volver al despliegue
anterior (`POST /v1/services/{id}/rollback`).

> **Sin probar contra Render.** Las llamadas a la API de Render están escritas según su
> documentación pública y no se pudieron ejecutar desde la sesión de trabajo (no hay clave). La
> verificación de versión sí se probó contra la URL pública. Antes de fiarte de la reversa,
> lánzala a mano una vez (*Run workflow*) con los secretos puestos.

**Qué hacer cuando sale en rojo «Producción no llegó a la versión X»:** abre
<https://dashboard.render.com> → el servicio → *Events* → el despliegue fallido → *Logs*. Lo más
común: un paquete que no instala, la migración de Alembic que falla al arrancar o la memoria
(512 MB) agotada al construir el panel.

## Interruptor de las tareas de fondo (`PATITAS_TAREAS_DE_FONDO`, #388)

Mientras la API corre hay tres tareas de fondo: el envío de avisos pendientes (#63), la revisión
de rescates sin aceptar (RN-08) y la de videos que nadie analizó a tiempo (#125). Cada una consulta
PostgreSQL. En Neon eso importa: la base solo se suspende tras **5 minutos sin consultas**, y
cada minuto despierta se descuenta de las 100 CU-h gratis del mes.

| Valor | Qué pasa |
|---|---|
| sin la variable, o `1` | Encendidas (lo normal). |
| `0` | La API **no arranca** ninguna tarea de fondo. El registro dice «Tareas de fondo APAGADAS». Los reportes, el panel y la PWA funcionan igual. |

Qué se pierde con `0`, y cómo se recupera:

- **Avisos:** confirmar un reporte sigue guardando sus avisos como *pendientes* en la misma
  transacción (nunca se pierden), pero nadie los envía. Al volver a `1` y reiniciar el servicio,
  la primera revisión los envía. El panel sigue diciendo «pendiente», nunca «enviado».
- **Escalamientos (RN-08):** un rescate crítico o alto sin aceptar no se escala a los 15/30 min.
  Al encender, la primera revisión escala los que ya vencieron.
- **Videos:** los que nadie analizó en 6 h no se cierran como fallidos hasta encender.

Cómo cambiarla en Render: *Environment* → `PATITAS_TAREAS_DE_FONDO` = `0` o `1` → *Save
changes* (Render reinicia el servicio). En local va en `.env`.
