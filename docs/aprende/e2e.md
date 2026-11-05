# Pruebas de punta a punta (e2e) con Playwright (#233)

## Qué prueban

Un navegador real recorre el caso completo de un rescate sobre una instancia de verdad
(API FastAPI + PostgreSQL + panel React compilado + PWA), con los datos de demostración:

| # | Prueba | Rol | Qué confirma |
|---|--------|-----|--------------|
| 1 | Descripción sin sentido | Ciudadano (390 px) | «Jsjsisoslqmwnabsnsnans…» muestra «Describe con palabras qué le pasa al animal.» (RN-01) |
| 2 | Reporte desde el teléfono | Ciudadano (390 px) | Recibe un código de 8 caracteres; sin scroll horizontal |
| 3 | Confirmar crítica | Veterinaria | Confirma (o ajusta con justificación, RN-16) y el reporte sale de la cola |
| 4 | Rol equivocado | API | Sin sesión 401; el veterinario no registra ingresos (403); el rescatista no ve la cola (403) |
| 5 | Rescate | Rescatista | Acepta la oferta, «Llegué al sitio» y «Trasladado al refugio» (RN-08) |
| 6 | Ingreso | Coordinador | Registra el ingreso con el código del reporte (#206) |
| 7 | Historiales | Veterinaria y rescatista | El código aparece en «Historial» y en «Mis rescates» |
| 8 | Seguimiento | Ciudadano (390 px) | 5 pasos hasta «Cerrado»; no aparece la descripción ni la dirección (RN-14) |

Las pruebas van en orden (`mode: "serial"`): cada una usa el código que creó la segunda.
Diferencia con `pytest`: allá se prueba cada pieza por separado (caja blanca y caja negra de
la API); aquí se prueba que las piezas juntas funcionan como las usa una persona.

## Cómo correrlas en Windows

1. Una base aparte, para no tocar `patitas` (nunca la de Neon):
   `CREATE DATABASE patitas_e2e;` y luego `POSTGRES_DB=patitas_e2e alembic upgrade head`.
2. Compila el panel: `cd panel && npm run build`.
3. Arranca la API con los datos de demostración (la contraseña la inventas tú, mínimo 12
   caracteres; no la escribas en ningún archivo del repositorio):

   ```bash
   export POSTGRES_DB=patitas_e2e PATITAS_DEMO_ACTIVA=true PATITAS_DEMO_CONTRASENA=<la tuya>
   uvicorn --factory app.api.main:crear_app --port 8010
   ```

4. En otra terminal, con la misma `PATITAS_DEMO_CONTRASENA`:

   ```bash
   cd e2e && npm ci
   E2E_CANAL=msedge npx playwright test     # Edge viene con Windows; en el CI es Chrome
   ```

Si una prueba falla a la mitad (por ejemplo, el rescatista quedó con un rescate activo), borra
y vuelve a crear `patitas_e2e`: el rescatista solo puede tener un rescate activo (RN-08).
El informe queda en `e2e/informe/index.html` y las capturas de los fallos en `e2e/resultados/`.

## En el CI

El job `e2e` de `.github/workflows/ci.yml` crea un PostgreSQL 17 temporal, compila el panel,
genera claves aleatorias que solo viven en esa ejecución, arranca la API y corre las pruebas
con el Chrome del runner. Si algo falla, sube el artefacto `e2e-capturas` (capturas, trazas
de Playwright y el log de la API). Para ver una traza: `npx playwright show-trace traza.zip`.

## Regresión visual (#316)

`e2e/aspecto.spec.mjs` toma una captura de 16 pantallas (página de inicio, PWA «Reportar» y la
pantalla de inicio de cada rol del panel, a 360 y 1440 px, en claro) y la compara con su
**captura base** guardada en `e2e/capturas/`. Si más del 1 % de los píxeles cambia
(`maxDiffPixelRatio` en `playwright.config.mjs`), la prueba falla: así un cambio de estilo no
pasa sin que alguien lo mire.

- Corre antes que las demás (orden alfabético), cuando solo están los datos de demostración.
- Lo que cambia en cada arranque (códigos aleatorios, «hace N min», cifras medidas) se tapa con
  una máscara magenta; lo demás debe coincidir.
- Las capturas base son de **Linux** (el Chrome del CI). En Windows las fuentes se dibujan
  distinto, por eso ahí la prueba se omite.

**Si falla en el CI**, descarga el artefacto `e2e-capturas`: en `resultados/` están, por cada
pantalla, `-expected.png` (la base), `-actual.png` (lo de ahora) y `-diff.png` (en rojo, lo que
cambió).

**Actualizar las capturas base a propósito** (solo cuando el cambio de aspecto es querido):

1. Borra de `e2e/capturas/` las capturas de las pantallas que cambiaste.
2. Sube la rama: el job `e2e` falla porque faltan esas bases y las adjunta, ya tomadas en Linux,
   en el artefacto `e2e-capturas` (carpeta `capturas/`).
3. Mira cada imagen nueva; si se ve como debe, cópiala a `e2e/capturas/`, haz commit y vuelve a
   subir. El CI queda en verde con la base nueva.

Nunca actualices una base para que «pase» sin mirar el `-diff.png`: esa es la regresión.
