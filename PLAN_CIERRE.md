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
| 0 | Este plan y `docs/guias/` en `.gitignore` | 1 | Plan en `main` | (este) |
| 1a | Video: diagnóstico en el issue #231 (hipótesis por probabilidad y cómo se descartó cada una) | — | Comentario en #231 | |
| 1b | Video: el nodo dice a la API que está vivo, su versión y por qué no hubo vista; el panel lo muestra | 2 | Prueba que falla antes y pasa después; contrato solo aditivo | |
| 1c | Video: robustez del nodo (reintento al subir la vista y al entregar, tiempo máximo del análisis, apagado a mitad) | 1–2 | Pruebas del trabajador con API caída, 5xx y reclamo vencido | |
| 1d | Video: el nodo se actualiza solo al arrancar (`git pull` + dependencias si cambiaron) + guía «qué hago yo» | 1 | Un solo comando arranca siempre el código de `main`; el nodo imprime su versión | |
| 1e | `video-humo.yml` ampliado: flujo completo contra una API local (subida → reclamo → vista → panel) | 1 | El flujo falla si la vista no llega a `GET …/vista.mp4` | |
| 2a | Guía 08: 3 parches TDD del percentil + script k6 en `scripts/operacion/` | 1 | `git am -3`; pruebas en verde | |
| 2b | Guía 12: cryptography 50.0.0, Bandit B310/B105 | 1 | `pip-audit` con 0 CVE (se pega la salida) | |
| 2c | Guía 13: OpenTelemetry, `/metrics` con token, logs JSON sin datos personales, apagado por defecto | 1 | Apagado: mismo comportamiento y mismo OpenAPI | |
| 2d | Guía 15: refactor de `rutas_reportes.py` | 1 | OpenAPI idéntico (comparación byte a byte del JSON) | |
| 2e | `ci-security.yml` (Bandit, Semgrep con `.semgrep/patitas.yml`, pip-audit, npm audit) | 1 | Flujo en verde en el PR | |
| 2f | Umbral de cobertura de 70 a 90 % | 1 | CI en verde con `--cov-fail-under=90` | |
| 3a | CHECK de RN-01 en `reportes` (migración `NOT VALID`, validación solo si los datos cumplen) + prueba de contrato | 1 | Migración aditiva probada en el CI; un `INSERT` corto falla | |
| 3b | Lista de reglas que viven solo en el código (propuesta, **sin aplicar**) | 1 | Tabla en este archivo, sección 5 | |
| 4a | Seguridad: OWASP ASVS 4.0.3 nivel 1 contra el código; `docs/tesis/seguridad.md` (control → cumple/no → evidencia) | 2–3 | Cada «no cumple» corregido con prueba o registrado como deuda | |
| 4b | Rendimiento: N+1, índices, triaje dentro de `POST /reportes`; medir antes y después | 1–2 | Cifras medidas (no estimadas) en `docs/tesis/pruebas.md` | |
| 4c | Quitar los 7 `# noqa: C901` de las fábricas de rutas (empieza por `crear_rutas_adopciones`) | 4–6 | OpenAPI idéntico en cada PR; Ruff sin `noqa` | |
| 4d | Pruebas: mutantes que sobreviven; E2E de video y de rescate | 2 | Pruebas nuevas en el CI | |
| 4e | Triaje con IA: `docs/tesis/triaje-ia.md` honesto (datos sintéticos, métricas, límites) + script de reentrenamiento con reportes reales | 1–2 | El documento no llama «validación» a métricas sintéticas | |
| 5a | H-1: qué hacer mientras llega ayuda, sin mostrar la prioridad (RN-14) | 1 | Prueba de que el texto no depende de la prioridad | |
| 5b | H-2: el aviso «sin conexión» solo con `navigator.onLine` falso | (con 5a) | Prueba e2e | |
| 5c | Estado «despertando el servidor» en PWA y panel; revisión por pantalla (360 px y escritorio, claro y oscuro) | 2–3 | axe en 0; capturas de regresión actualizadas | |
| 5d | Portada #329: unir si sigue en verde; lo pendiente de #328 si cabe | 1 | #329 integrado | |
| 6a | `respaldo.yml`: versión del servidor (`SHOW server_version_num`) con mensaje claro; alerta si el último respaldo exitoso tiene más de 26 h | 1 | Flujo válido; no se ejecuta contra Neon desde aquí | |
| 6b | `deploy.yml` con *healthcheck* y *rollback* (Guía 11): solo si no pide claves nuevas; si las pide, queda listo con los pasos | 1 | Documentado qué clave falta | |
| 7 | Release v1.3.0: `CHANGELOG.md`, `DEUDA_TECNICA.md`, `ESTADO_PROYECTO.md`, etiqueta, verificación en producción | 1 | `/app/` 200, `/reportes/NOEXISTE` 404, humo del video | |
| 8a | `docs/piloto/`: consentimiento, 4 tareas, hoja de observación (P01…), SUS con fórmula | 1 | Sin datos inventados; resultados en blanco | |
| 8b | `docs/aprende/sustentacion-final.md`: arquitectura por capas, recorrido de un reporte, decisiones y 20 preguntas con evidencia | 1 | Cada respuesta apunta a un archivo que existe | |
| 8c | `docs/aprende/guion-demo.md` actualizado (5 minutos) | (con 8b) | | |

## 4. Lo que tiene que hacer Brayan (se va completando)

- (pendiente de completar al cerrar cada trabajo)

## 5. Propuestas que esperan decisión de Brayan

- (se llena en el trabajo 3b)

## 6. Bitácora de la sesión

- 16-nov: fase 0. Línea base medida (806 pasan / 174 omitidas sin base). Plan escrito.
