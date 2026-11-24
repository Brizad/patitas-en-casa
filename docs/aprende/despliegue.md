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

## Consumo esperado de Neon (#390)

**Cómo cobra Neon (plan gratis):** 100 CU-h al mes. Una CU-h es una unidad de cómputo durante una
hora; la base corre con 0,25 CU, así que el mes alcanza para **unas 400 horas despierta**. La base
solo se suspende tras **5 minutos sin consultas**, y cualquier consulta la despierta.

**Qué la despertaba antes:** avisos cada 15 s, escalamientos y videos cada 60 s, el sondeo cada
30 min y el nodo de video cada 15 s. Nunca dormía: 720 h × 0,25 = **180 CU-h al mes**, así que
el límite se acababa hacia el día 17 (coincide con los despliegues fallidos desde el 17/20-nov).

**Qué la despierta ahora:**

| Quién | En reposo | Con trabajo |
|---|---|---|
| Avisos | revisan al arrancar y tras cada petición que cambia datos; sin pendientes, a los 15 s, 30 s, 1, 2, 4, 8, 16 y 30 min | cada 15 s mientras salgan avisos |
| Escalamientos (RN-08) | nada | una revisión justo cuando vence el próximo rescate (15/30 min) |
| Videos | nada | una revisión cuando el video más antiguo cumple 6 h |
| Nodo de video | pregunta cada 15 s → 5 min, pero la API responde **sin consultar la base** si sabe que no hay trabajos | igual que antes |
| Sondeo de GitHub | desactivado; al reactivarlo, cada 6 h y solo `/app/` (no toca la base) | — |
| Respaldo diario | un `pg_dump` al día (≈ 6 min despierta) | — |

**Cuentas para un mes de uso normal del refugio** (supuesto: 2 sesiones del personal al día de
1 hora cada una, 5 reportes ciudadanos sueltos al día y el respaldo):

| Escenario | Horas despierta al mes | CU-h |
|---|---|---|
| Antes de #390 (siempre despierta) | 720 | **180** |
| Ahora, UptimeRobot **pausado** (Render se duerme 15 min después de la última visita): cada sesión deja ≈ 13 min de cola (los 5 min de Neon más las revisiones de avisos a 0,25 · 0,75 · 1,75 · 3,75 · 7,75 min) | (2 × 73 + 5 × 13 + 6) min × 30 ≈ 108 | **≈ 27** |
| Ahora, UptimeRobot **activo** contra `/app/` (Render nunca duerme): se suma la revisión de avisos cada 30 min en reposo, ≈ 5,5 min despierta de cada 30 | ≈ 108 + 110 | **≈ 55** |

Lo que hay que saber de cada escenario:

- **UptimeRobot pausado** cumple el objetivo (< 30 CU-h), pero si Render está dormido **nadie
  escala a tiempo** un rescate sin aceptar: se escala en cuanto alguien vuelva a entrar (la
  revisión del arranque escala los vencidos). Para la demo o un piloto real, conviene activarlo.
- **UptimeRobot activo** (solo contra `/app/`, que no toca la base) mantiene RN-08 a tiempo y
  evita el arranque en frío, y gasta ≈ 1,8 CU-h por día. Para un mes completo no alcanza; para
  los días de la demo, sí.
- Con `PATITAS_TAREAS_DE_FONDO=0` no hay ninguna revisión en reposo, pero tampoco avisos ni
  escalamientos (ver arriba).

## RN-08 con Render dormido: propuesta (25-nov, **sin aplicar**)

**El problema.** RN-08 pide escalar al coordinador un rescate crítico sin aceptar a los 15 min
(alto: 30 min). Quien lo hace es la tarea de fondo de la API (`ServicioRescates.revisar_escalamientos`).
Si Render está dormido no hay proceso: el escalamiento ocurre cuando alguien vuelve a entrar
(la revisión del arranque escala los vencidos), que puede ser horas después. Render se duerme a
los 15 min sin visitas, justo el plazo del crítico.

**Cuenta base** (de la sección de consumo): despertar Render para revisar deja Neon despierto
≈ 13 min (arranque, los 5 min de Neon y las revisiones de avisos mientras Render sigue arriba).
Con 0,25 CU: 0,25 × 13 / 60 ≈ **0,054 CU-h por despertar**, si no coincide con uso real.

| Opción | Cómo funciona | Escala a tiempo | Costo en Neon | Complejidad |
|---|---|---|---|---|
| A. Escalar al leer | `GET /cola`, `GET /rescates/ofertas` y el inicio de sesión llaman a `revisar_escalamientos()` antes de responder | Solo cuando alguien entra; el correo al coordinador sale tarde | ≈ 0 (la base ya está despierta por esa petición) | Baja: 3 llamadas y sus pruebas |
| B. Despertador con retraso (recomendada) | Al confirmar un crítico o alto, la API programa **una** llamada diferida (por ejemplo, Upstash QStash: mensaje con `delay` de 15 o 30 min) a un `POST /interno/escalamientos` protegido con token. Esa llamada despierta Render y revisa | Sí, con el retraso del arranque en frío (30 a 60 s) | ≈ 0,054 CU-h por rescate que nadie acepta a tiempo; con 5 al día y ninguno coincidiendo con uso: 5 × 30 × 0,054 ≈ **8 CU-h/mes** (techo) | Media: un servicio externo, su secreto y una ruta nueva (aditiva) |
| C. UptimeRobot solo mientras haya ofertas | La API pausa o reanuda el monitor con la API de UptimeRobot al ofrecer y al aceptar o escalar | Sí | Render despierto mientras haya ofertas; las revisiones de avisos (hasta cada 30 min) despiertan Neon ≈ 5,5 min de cada 30 | Media-alta: depende de otra API y de no olvidar pausar |
| D. UptimeRobot siempre contra `/app/` | Ya documentado arriba | Sí | ≈ 1,8 CU-h por día (≈ 55 CU-h/mes con uso normal) | Ninguna |
| E. Cron de GitHub cada 10 min | Un flujo que pide `/app/` | Con hasta 10 min de atraso | Mantiene Render despierto casi siempre: parecido a D | Baja, pero gasta minutos de Actions |

**Recomendación:** A + B. A no cuesta nada y cubre el caso común (el coordinador o un rescatista
abren el panel). B garantiza los 15/30 min con un costo acotado al número de rescates sin aceptar.
D queda para los días de la demo, porque además evita el arranque en frío.

**Qué no cambia:** RN-08 (tiempos en `app/config.py`, un solo aviso por la llave de
`escalamientos`), los contratos existentes (B agrega una ruta interna, no cambia ninguna) y el
outbox de avisos. Antes de aplicar B hay que decidir el servicio externo y crear su secreto en
Render (eso lo hace el autor).
