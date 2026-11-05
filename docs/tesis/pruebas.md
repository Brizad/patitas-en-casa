# Plan y reporte de pruebas

## 1. Plan

### Objetivo
Demostrar que cada requisito del ERS tiene una prueba automática que lo verifica y que las
reglas de negocio (RN-01 a RN-16) no se rompen con cada cambio. Ningún PR se une a `main` sin
el CI en verde (`gh pr checks`).

### Niveles y técnicas

| Nivel | Técnica | Herramienta | Qué cubre | Dónde |
|-------|---------|-------------|-----------|-------|
| Unidad | Caja blanca: ramas, límites y casos de error de cada regla | pytest | Dominio y servicios con repositorios en memoria (triaje, RN-02/RN-03, cupos, adopción, video, límites) | `tests/test_*.py` |
| Contrato | La misma prueba sobre dos implementaciones | pytest + marcador `postgres` | Repositorios en memoria y en PostgreSQL (reportes, rescates, avisos, video) | `test_repositorio_contrato.py`, `test_consultas_acotadas.py`… |
| Integración con la base | Caja blanca contra PostgreSQL real | pytest + fixture `bd_limpia` | Concurrencia (RN-04, RN-08), migraciones, bitácora inmutable | Pruebas con `@pytest.mark.postgres` |
| API | Caja negra: solo HTTP, sin mirar el código | `fastapi.testclient` | Códigos 200/201/401/403/404/409/413/422/429 de cada endpoint y su contenido | `test_api*.py`, `test_video_api.py`… |
| Interfaz (unidad) | Caja blanca de funciones puras del panel | Vitest | Mensajes, navegación por rol, clientes de la API | `panel/src/*.test.ts` |
| Punta a punta | Caja negra en un navegador real | Playwright | Flujo completo ciudadano → veterinario → rescatista → coordinador → seguimiento, y errores | `e2e/flujo.spec.mjs` |
| Accesibilidad | Automática | axe-core y Lighthouse | Todas las pantallas, cada rol, modo claro y oscuro | `scripts/accesibilidad/revisar.mjs` |
| Seguridad | Estática y dinámica | gitleaks, Ruff, OWASP ZAP | Secretos en el historial, complejidad ≤ 10, cabeceras y riesgos altos | `ci.yml`, `zap.yml` |
| Carga | Medición | `prueba_carga.py` | RNF-01 y RNF-14 en local | `scripts/operacion/` |
| Mutación | Calidad de las pruebas: ¿fallan si el código cambia? | mutmut 3 (WSL2) | Reglas de `app/triaje`, `app/cupos`, `app/rescates` y `app/adopciones/reglas.py` | `scripts/operacion/mutacion.sh` |
| Nodo de video | Humo con videos reales de licencia libre | GitHub Actions | La tubería completa (MediaPipe + DeepLabCut) | `video-humo.yml` |

### Criterios de aceptación
- 100 % de las pruebas en verde; cobertura de líneas ≥ 70 % (RNF-10, `--cov-fail-under=70`).
- Ruff sin errores y complejidad ciclomática ≤ 10 (C901).
- axe-core con 0 fallas y Lighthouse 100 en las pantallas públicas (RNF-11).
- e2e: el flujo completo pasa en Chrome sobre PostgreSQL.
- Las pruebas que necesitan base **fallan** (no se omiten) en el CI: `PATITAS_EXIGIR_POSTGRES=1`.

### Entorno
CI de GitHub Actions en `ubuntu-24.04`: Python 3.11, PostgreSQL 17 en contenedor (base de
pruebas temporal), Node 22 y Google Chrome del runner. Producción usa PostgreSQL 18 (Neon);
las pruebas no tocan esa base.

## 2. Reporte (4 de noviembre de 2026)

Corrida del CI sobre `main` en el commit `ffde3c4` (run `41920309563`), resultado **success**:

| Suite | Resultado | Detalle |
|-------|-----------|---------|
| pytest | **864 pasaron**, 0 fallaron, 0 omitidas | 2 min 29 s; 172 usan PostgreSQL (`-m postgres`); 400 están en archivos que prueban la API por HTTP |
| Cobertura | **97,22 %** | 4 239 sentencias, 118 sin cubrir (mínimo exigido: 70 %) |
| Ruff | 0 errores | incluye C901 ≤ 10 |
| gitleaks | 0 secretos | sobre todo el historial, con auto-prueba |
| Vitest (panel) | **58 pasaron** en 9 archivos | |
| e2e (Playwright) | **8 pasaron** | 17,2 s; job `e2e` |
| axe-core | **50 revisiones, 0 fallas** | cada pantalla y rol, claro y oscuro |
| Lighthouse | **100** en las 4 pantallas públicas | Inicio, Reportar, Consultar e Iniciar sesión |

### Pruebas de mutación (5 de noviembre de 2026, #272)

`mutmut` cambia el código a propósito (un `<` por `<=`, un `and` por `or`, borra una condición…)
y corre las pruebas: si ninguna falla, el mutante **sobrevive** y hay un hueco en las pruebas.
Puntaje = (muertos + timeouts) / (mutantes con pruebas). Corrida completa: **1 352 mutantes en
837 s** (WSL2, 6 procesos), por eso no está en el CI (más de 10 minutos).

| Módulo | Mutantes | Sin pruebas* | Muertos | Timeout | Sobreviven | Puntaje antes | Puntaje después |
|---|---|---|---|---|---|---|---|
| `app/triaje` | 414 | 0 | 333 | 64 | 17 | 95,2 % | **95,9 %** |
| `app/cupos` | 358 | 259 | 84 | 11 | 4 | 84,8 % | **96,0 %** |
| `app/rescates` | 564 | 195 | 315 | 23 | 31 | 88,1 % | **91,6 %** |
| `app/adopciones/reglas.py` | 16 | 0 | 12 | 4 | 0 | 62,5 % | **100 %** |
| **Total** | 1 352 | 454 | 744 | 102 | 52 | 90,5 % | **94,2 %** |

\* Sobre todo los repositorios PostgreSQL: en WSL no hay base y sus pruebas se omiten; en el CI
sí corren contra PostgreSQL (172 pruebas con el marcador `postgres`).

**Huecos que encontró y que ahora cubre `tests/test_mutacion.py`** (33 de los 37 mutantes que
sobrevivían en esas funciones mueren): ninguna prueba vigilaba la **regla del patio** de RN-05
(quitar el `not` pasaba); el **empate de prioridad** entre texto y video (RN-07, `<` por `<=`);
el **límite exacto** de letras de una nota clínica; que **otro rescatista** no pueda cerrar un
rescate ajeno en camino (`and` por `or`); que se puedan elegir **las 10 comunas** (`<=` por `<`);
y que en el escalamiento (RF-23) un caso ya tomado, aún no vencido o escalado por otro proceso
**no frene a los demás** (`continue` por `break`).

**Lo que sigue vivo, a propósito:** mutantes que solo cambian el texto de un mensaje interno y
mutantes equivalentes (por ejemplo, pasar `None` como hora a un repositorio en memoria que no la
guarda). Matarlos no protege ninguna regla.

Cómo repetirlo (en WSL2 o Linux, con Python 3.12):

```bash
bash scripts/operacion/mutacion.sh
cd ~/patitas-mut && mutmut browse   # recorre cada sobreviviente con su diff
```

### Medido antes y que no se repitió hoy
- RNF-01 y RNF-14 (carga): p95 = 2,84 s con 30 concurrentes y ≈ 58 000 reportes/hora, **en
  local** (#120). En Render no se midió para no llenar la base real de reportes falsos.
- RNF-02 (video de 60 s en ≤ 3 min): 36 a 82 s por video en la prueba de humo (#135, #137).
- RNF-05 (OWASP ZAP): 0 riesgos altos en la última corrida a mano (#122).

### Pendiente (no se puede medir desde el código)
- **RNF-06** (usabilidad: 80 % reporta en ≤ 90 s y SUS ≥ 70): necesita 10 personas reales;
  guía en `docs/aprende/piloto.md` y script `scripts/operacion/resultados_piloto.py`.
- **RNF-03** (recall ≥ 0,95 en crítica **con datos de veterinarios**): hoy solo hay datos
  sintéticos y el análisis de errores con textos escritos por el asistente
  (`docs/aprende/errores-ia-texto.md`).
- **RNF-04** (99 % de disponibilidad): el sondeo y UptimeRobot vigilan, pero no hay una
  medición de un mes.
- Escuchar el recorrido con un lector de pantalla (parte manual de RNF-11).

### Cómo repetir
```bash
pytest --cov=app                      # con PATITAS_EXIGIR_POSTGRES=1 para no omitir las de base
cd panel && npm test
cd e2e && npx playwright test         # guía: docs/aprende/e2e.md
```
