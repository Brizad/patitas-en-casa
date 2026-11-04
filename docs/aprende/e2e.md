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
