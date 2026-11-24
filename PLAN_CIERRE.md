# Plan de cierre — Patitas en Casa (entrega: 30 de noviembre de 2026)

Este archivo es la **única fuente para retomar** el cierre: si una sesión se corta, la siguiente
lee esto, mira la tabla de trabajos y sigue por el primero sin marcar. Cada trabajo integrado
se marca con su número de PR. Reglas de trabajo: `CLAUDE.md`.

Punto de partida: `main` en `f86be5c` (16 de noviembre de 2026), copia local limpia y al día.

## 1. Diagnóstico del estado real

Comprobado el 16-nov-2026 (lo que no se pudo comprobar se dice):

| Qué | Estado | Cómo se comprobó |
|---|---|---|
| Código | 104 módulos en `app/`, 101 archivos de prueba, 34 migraciones | `find`, `ls migraciones/versions` |
| Suite sin base | 806 pasan, 174 se omiten (las de PostgreSQL), Ruff limpio | corrida local de hoy |
| Suite completa | 980 pytest, 97,48 % de cobertura (el CI exige solo 70 %) | `ESTADO_PROYECTO.md` (CI de `8094ad4`); no se repitió hoy |
| Producción | `/app/` 200; 68 rutas; las de la vista previa existen; CSP con `media-src blob:`; Cloudflare no guarda nada (`cf-cache-status: DYNAMIC`) | `curl` sin credenciales |
| Vista previa del video en producción | **No se ve** (#231 sigue abierto). En local sí | reporte del autor; no hay acceso a Neon ni al nodo |
| Complejidad | 7 fábricas de rutas con `# noqa: C901` (`rutas_admin`, `rutas_adopciones`, `rutas_refugio`, `rutas_reportes`, `rutas_rescates`, `rutas_triaje`, `video`) | `grep` |
| Issues | 40 abiertos; la mayoría ya están resueltos por PR que decían «Cierra #N» (GitHub solo entiende *Closes/Fixes*) | `gh issue list` |
| PR abiertos | #329 (portada, parte 1): en verde y sin conflictos | `gh pr checks 329` |
| Repositorio | **Público** (`CLAUDE.md` todavía dice privado): el instalador del nodo se descarga sin credenciales | `gh repo view`, `curl` anónimo: 200 |
| Versión | `info.version` de la API dice `1.1.0` aunque ya se publicó v1.2.0 | `/openapi.json` de producción |

**Este equipo no es el del nodo de video**: aquí no hay WSL, ni PostgreSQL local, ni `.env`.
Consecuencias: (1) las pruebas con base y las migraciones se comprueban solo en el CI (contenedor
de PostgreSQL, equivalente a `patitas_test`); (2) el nodo de video no se puede correr en esta
sesión: lo que dependa de él queda como paso para Brayan; (3) la carpeta de evidencias de las
guías no está en `Documents\Proyectos\…` sino en
`2 CORTE\SEMANA 7\ENTREGABLE\Guias_SW2_Semana7_Brayan_Amado\evidencias` (su guía se llama
`ExplicacionContenidoEvidencias.md`, no `LEEME.md`; el contenido coincide con lo descrito).

## 2. Riesgos, ordenados por impacto en la entrega

| # | Riesgo | Impacto | Qué lo baja |
|---|---|---|---|
| R1 | La vista previa del video no se ve en producción y nadie puede decir por qué: ni el panel ni la API saben si el nodo está vivo, qué versión corre o por qué no subió la vista | Alto: es el corazón de la demo | Trabajo 1 |
| R2 | El nodo vive en otra carpeta (`~/patitas` en WSL) y solo se actualiza si Brayan repite la instalación **y lo reinicia**: es fácil que corra código viejo sin que nadie lo note | Alto | Trabajo 1 |
| R3 | El nodo depende de un solo PC (el de Brayan); si se apaga a mitad, el reporte debe seguir con el texto | Medio (ya hay falla segura; falta probarla y documentarla) | Trabajo 1 |
| R4 | Piloto con usuarios (RNF-06) sin hacer: sin datos no hay resultados de usabilidad | Alto para la sustentación; depende de Brayan | Trabajo 8 (material) |
| R5 | El triaje con IA solo está validado con datos sintéticos; presentarlo como validado sería deshonesto | Alto ante el jurado | Trabajo 4 (documento y reentrenamiento) |
| R6 | El CI no escanea seguridad (SAST/SCA) y exige 70 % cuando hay 97 %: una regresión no se notaría | Medio | Trabajo 2 |
| R7 | RN-01 vive solo en el código: un `INSERT` directo puede saltársela | Medio | Trabajo 3 |
| R8 | Arranque en frío de Render: la primera petición puede tardar ~1 min y la interfaz parece rota | Medio en la demo | Trabajo 5 |
| R9 | Respaldo: si `pg_dump` y el servidor no coinciden de versión, falla sin decir por qué; nadie avisa si no hubo respaldo | Medio | Trabajo 6 |
| R10 | Alcance: son ~35 PR; puede no caber todo antes del 30-nov | Medio | El orden de la tabla: primero lo que se muestra y se sustenta |

## 3. Trabajos

Estimación en PR (cada uno ≤ 300 líneas). «Hecho» solo con PR integrado y CI en verde.

| ID | Trabajo | Est. | Criterio de aceptación | PR |
|---|---|---|---|---|
| 0 | Este plan y `docs/guias/` en `.gitignore` | 1 | Plan en `main` | #331 ✅ |
| 1a | Video: diagnóstico en el issue #231 (hipótesis por probabilidad y cómo se descartó cada una) | — | Comentario en #231 | ✅ comentarios en #231 |
| 1b | Video: el nodo dice a la API que está vivo, su versión y por qué no hubo vista; el panel lo muestra | 2 | Prueba que falla antes y pasa después; contrato solo aditivo | #332, #333 ✅ |
| 1c | Video: robustez del nodo (reintento al subir la vista y al entregar, tiempo máximo del análisis, apagado a mitad) | 1–2 | Pruebas del trabajador con API caída, 5xx y reclamo vencido | #334 ✅ |
| 1d | Video: el nodo se actualiza solo al arrancar (`git pull` + dependencias si cambiaron) + guía «qué hago yo» | 1 | Un solo comando arranca siempre el código de `main`; el nodo imprime su versión | #335 ✅ |
| 1e | `video-humo.yml` ampliado: flujo completo contra una API local (subida → reclamo → vista → panel) | 1 | El flujo falla si la vista no llega a `GET …/vista.mp4` | #336 ✅ (humo real en verde: run 44011576681) |
| 2a | Guía 08: 3 parches TDD del percentil + script k6 en `scripts/operacion/` | 1 | `git am -3`; pruebas en verde | #338 ✅ |
| 2b | Guía 12: cryptography 50.0.0, Bandit B310/B105 | 1 | `pip-audit` con 0 CVE (se pega la salida) | #340 ✅ |
| 2c | Guía 13: OpenTelemetry, `/metrics` con token, logs JSON sin datos personales, apagado por defecto | 1 | Apagado: mismo comportamiento y mismo OpenAPI | #349 ✅ |
| 2d | Guía 15: refactor de `rutas_reportes.py` | 1 | OpenAPI idéntico (comparación byte a byte del JSON) | #359 ✅ |
| 2e | `ci-security.yml` (Bandit, Semgrep con `.semgrep/patitas.yml`, pip-audit, npm audit) | 1 | Flujo en verde en el PR | #351 ✅ |
| 2f | Umbral de cobertura de 70 a 90 % | 1 | CI en verde con `--cov-fail-under=90` | #367 ✅ |
| 3a | CHECK de RN-01 en `reportes` (migración `NOT VALID`, validación solo si los datos cumplen) + prueba de contrato | 1 | Migración aditiva probada en el CI; un `INSERT` corto falla | #342 ✅ |
| 3b | Lista de reglas que viven solo en el código (propuesta, **sin aplicar**) | 1 | Tabla en este archivo, sección 5 | pendiente (no bloquea la entrega) |
| 4a | Seguridad: OWASP ASVS 4.0.3 nivel 1 contra el código; `docs/tesis/seguridad.md` (control → cumple/no → evidencia) | 2–3 | Cada «no cumple» corregido con prueba o registrado como deuda | #361, #362, #363 ✅ |
| 4b | Rendimiento: N+1, índices, triaje dentro de `POST /reportes`; medir antes y después | 1–2 | Cifras medidas (no estimadas) en `docs/tesis/pruebas.md` | #365 ✅ (N+1 de `/indicadores`) |
| 4c | Quitar los 7 `# noqa: C901` de las fábricas de rutas (empieza por `crear_rutas_adopciones`) | 4–6 | OpenAPI idéntico en cada PR; Ruff sin `noqa` | #357, #359, #375, #376, #377, #378, #379 ✅ (ya no queda ningún `noqa: C901`) |
| 4d | Pruebas: mutantes que sobreviven; E2E de video y de rescate | 2 | Pruebas nuevas en el CI | #381 ✅ (huecos de cobertura). Los E2E de rescate y de video ya existían (`e2e/flujo.spec.mjs`, `video-humo.yml`). **Mutantes con mutmut: no se corrieron** (pide WSL2, `scripts/operacion/mutacion.sh`) |
| 4e | Triaje con IA: `docs/tesis/triaje-ia.md` honesto (datos sintéticos, métricas, límites) + script de reentrenamiento con reportes reales | 1–2 | El documento no llama «validación» a métricas sintéticas | #355 ✅ |
| 5a | H-1: qué hacer mientras llega ayuda, sin mostrar la prioridad (RN-14) | 1 | Prueba de que el texto no depende de la prioridad | #344 ✅ |
| 5b | H-2: el aviso «sin conexión» solo con `navigator.onLine` falso | (con 5a) | Prueba e2e | #344 (abierto) |
| 5c | Estado «despertando el servidor» en PWA y panel; revisión por pantalla (360 px y escritorio, claro y oscuro) | 2–3 | axe en 0; capturas de regresión actualizadas | PWA #344 ✅, panel #373 ✅ (CI con axe y capturas en verde; **no se revisó a ojo en el navegador**) |
| 5d | Portada #329: unir si sigue en verde; lo pendiente de #328 si cabe | 1 | #329 integrado | #329 ✅ (parte 1; lo demás de #328 sigue pendiente) |
| 6a | `respaldo.yml`: versión del servidor (`SHOW server_version_num`) con mensaje claro; alerta si el último respaldo exitoso tiene más de 26 h | 1 | Flujo válido; no se ejecuta contra Neon desde aquí | #353 ✅ |
| 6b | `deploy.yml` con *healthcheck* y *rollback* (Guía 11): solo si no pide claves nuevas; si las pide, queda listo con los pasos | 1 | Documentado qué clave falta | #383 ✅ (verificación sin claves; reversa pide `RENDER_API_KEY` y `RENDER_SERVICE_ID`, sin probar) |
| 7 | Release v1.3.0: `CHANGELOG.md`, `DEUDA_TECNICA.md`, `ESTADO_PROYECTO.md`, etiqueta, verificación en producción | 1 | `/app/` 200, `/reportes/NOEXISTE` 404, humo del video | #371 ✅ y etiqueta v1.3.0 ✅; **verificación en producción: NO pasó** (ver bitácora del 20-nov) |
| 8a | `docs/piloto/`: consentimiento, 4 tareas, hoja de observación (P01…), SUS con fórmula | 1 | Sin datos inventados; resultados en blanco | #347 ✅ |
| 8b | `docs/aprende/sustentacion-final.md`: arquitectura por capas, recorrido de un reporte, decisiones y 20 preguntas con evidencia | 1 | Cada respuesta apunta a un archivo que existe | **para después** (rama local `docs/sustentacion-final`, sin PR) |
| 8c | `docs/aprende/guion-demo.md` actualizado (5 minutos) | (con 8b) | | **para después** |

## 4. Lo que tiene que hacer Brayan (se va completando)

**URGENTE — producción no se actualiza (20-nov):** entra a Render → el servicio → *Events* →
el despliegue del commit `9a851c2` (o cualquiera posterior, todos fallaron) → *Logs*, y pégame
las últimas 30 líneas. Enlace de uno de ellos:
`https://dashboard.render.com/web/srv-dbhdgno473hc739mege0/deploys/dep-dc0cd8e0tbcc73bkm1hg`.
Hasta que se arregle, la entrega muestra la versión 1.1.0 y no tiene nada de lo de #332 en adelante.

**Reversa automática (opcional):** secretos `RENDER_API_KEY` y `RENDER_SERVICE_ID` en GitHub
(pasos en `docs/aprende/despliegue.md`).

**Mutantes (opcional):** en WSL2, `bash scripts/operacion/mutacion.sh` y mira los que sobreviven.

**Nodo de video (en el PC que tiene WSL; una sola vez, unos 5 min si ya estaba instalado):**

1. Abre **Ubuntu** y, si el nodo está corriendo, deténlo con **Ctrl+C**.
2. Pega (clic derecho) y espera a que diga «Listo»:
   `curl -fsSL https://raw.githubusercontent.com/Brizad/patitas-en-casa/main/servicios/video/instalar_nodo.sh | bash`
   (instala ffmpeg si faltaba y deja la marca para que el nodo se actualice solo).
3. Arráncalo: `bash ~/patitas/servicios/video/arrancar_nodo.sh`. Debe decir
   `nodo de video 1.3.0 trabajando contra https://patitas-en-casa-pnnk.onrender.com`.
   Si dice «AVISO: falta ffmpeg», corre `sudo apt install -y ffmpeg` y vuelve a arrancar.
4. Envía un reporte con video desde la PWA y ábrelo en el panel como veterinaria. Ahora el
   panel dice si el equipo está apagado o viejo y, si no hay vista, **el motivo exacto**.
5. Escribe en el issue #231 qué viste (reproductor, o el motivo que mostró el panel).

**Render:** si en *Environment* existe `PATITAS_VIDEO_DIR`, **bórrala** (con ella las vistas
se guardan en el disco temporal y se pierden en cada reinicio). No se pudo comprobar desde aquí.

**Observabilidad (opcional, cuando se integre 2c):** en Render → *Environment*:
`PATITAS_OBSERVABILIDAD=1` y `PATITAS_METRICAS_TOKEN=<un valor aleatorio largo>`. Sin el
token, `/metrics` no existe. Por defecto queda apagada.

**Neon (solo lectura, antes o después de que se despliegue 3a):** en el editor SQL,
`SELECT codigo FROM reportes WHERE char_length(btrim(descripcion)) < 20;` Debe dar 0 filas.
Si diera alguna, avisa antes de confirmar o descartar esos reportes.

**`CLAUDE.md`:** dice que el repositorio es privado; hoy es **público** (`gh repo view`).

## 5. Propuestas que esperan decisión de Brayan

- (se llena en el trabajo 3b)

## 6. Bitácora de la sesión

- 16-nov: fase 0. Línea base medida (806 pasan / 174 omitidas sin base). Plan escrito.
- 16/17-nov: trabajo 1 completo (#332 a #336). Diagnóstico en #231: el lado de la API quedó
  comprobado con componentes reales en el CI; la causa más probable es el nodo de WSL (código
  anterior al 2-nov o sin ffmpeg). No se pudo comprobar: este equipo no tiene WSL.
- 17-nov: Guía 08 (#338) y Guía 12 (#340; `pip-audit`: «No known vulnerabilities found»).
- 17-nov: **Guía 13: el parche no instala tal cual.** Fija OpenTelemetry 1.37.0 y FastAPI
  0.142.1 exige `opentelemetry-api>=1.44`. Pines que sí resuelven: `opentelemetry-sdk==1.45.2`,
  `opentelemetry-exporter-otlp-proto-http==1.45.2`, `opentelemetry-exporter-prometheus==0.66b2`.
  Además el parche dejaba `/metrics` **pública** si se activaba sin token: se cerró (sin token
  no hay ruta) y el SDK solo se carga al activarla. Probado en local en la rama
  `tmp/guia13-local` (no subida): 7 pruebas, OpenAPI idéntico.
- 17-nov: Guía 15 probada encima (rama local `tmp/guia15-local`): OpenAPI idéntico byte a
  byte y `rutas_reportes.py` sin `noqa: C901`.
- 17-nov: `pip-audit -r requirements-dev.txt` marca `pytest 8.4.2` (PYSEC-2026-1845, se
  corrige en 9.0.3): pendiente para 2e.
- Para retomar: las ramas `tmp/*` son locales de este equipo; si no existen, se rehacen con
  `git am -3` sobre `main` en el orden 13 → 15 y los ajustes descritos arriba.
- 20-nov: se integran #357 (adopciones sin `noqa`), #363 (ASVS), #365 (N+1) y #367 (cobertura 90 %).
  #357 falló tras traer `main` porque `tests/test_complejidad.py` aún listaba `rutas_reportes.py`
  como pendiente: se corrigió. Ramas `tmp/*` borradas (su contenido ya está en #349 y #359).
  Quedan 5 fábricas con `noqa: C901`: admin, refugio, rescates, triaje y video.
- 8b y 8c quedan **para después** por indicación del autor.
- 20-nov (tarde): release v1.3.0 publicado (#371, etiqueta y release en GitHub). **Producción no
  la tiene**: los despliegues de Render fallan desde `9a851c2` (6 seguidos; los anteriores, hasta
  el 17-nov, salieron bien) y la API sigue diciendo `1.1.0`. Se comprobó con
  `gh api repos/Brizad/patitas-en-casa/deployments`. El registro de Render no se puede leer desde
  aquí. Al final de la sesión `/app/` tampoco respondía en 90 s (puede estar dormido). Cambios
  entre el último despliegue bueno y el primero malo: solo `rutas_adopciones.py` (#357), cuyo CI
  (incluido el e2e contra la app real) pasó. Se sospecha de Render, no del código; sin el registro
  no se afirma.
- 20-nov (tarde): 5c panel (#373), 4c completo (#375 a #379), 4d (#381), 6b (#383, `deploy.yml`
  que sí habría avisado de esto). 3b sigue pendiente; 8b y 8c **para después**.

## 7. Noche del 24-nov: Neon suspendido por consumo

**Causa:** la base de Neon nunca dormía (avisos cada 15 s, escalamientos y videos cada 60 s,
UptimeRobot y el sondeo cada 30 min). Se agotaron las 100 CU-h gratis del mes (se reinician el
30-nov) y desde `9a851c2` todo despliegue de Render falla porque `alembic upgrade head` no conecta.
Producción solo debe estar viva cuando alguien la usa; el desarrollo sigue en el PC del autor.

| # | Trabajo | Estado | PR |
|---|---|---|---|
| 1 | Sondeo desactivado (`gh workflow disable`) y preparado: cada 6 h, solo `/app/` | hecho (desactivado el 24-nov) | #387 |
| 2 | Interruptor `PATITAS_TAREAS_DE_FONDO` | hecho | #389 |
| 3 | Tareas de fondo sin consultas en reposo | hecho en 3 partes | #391, #392, #393 |
| 4 | Flujo `restaurar-a-neon-nuevo.yml` | hecho; lanzado sin el secreto: falla con «Falta el secreto NEON_DATABASE_URL_NUEVA» (ejecución 45338382347) | #395 |
| 5 | Panel: 5xx o respuesta sin JSON → «El servidor tuvo un problema…» | hecho (el e2e encontró que un JSON null se volvía {}: corregido antes de unir) | #397 |
| 6 | `scripts/dev/arrancar_local.ps1` y `docs/aprende/desarrollo-local.md` | hecho; probado sin `.env` (se detiene y explica) y completo contra un PostgreSQL 17 temporal | #399 |
| 7 | Revisión visual con Playwright y 10 correcciones | 7a: capturas «antes» y hallazgos (#400); faltan los arreglos | |

Bitácora de la noche:
- `git fetch` falló una vez por red y al segundo intento sí. `main` en `19c9afe`, sin PR abiertos.
