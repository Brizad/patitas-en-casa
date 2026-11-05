# Estado del proyecto Patitas en Casa (para retomar en cualquier sesión)

Lee primero `CLAUDE.md`, `docs/aprende/avance.md` y `git log --oneline -20`.
Producción: https://patitas-en-casa-pnnk.onrender.com (Render + Neon PostgreSQL 18 + Mailjet).
El repositorio es **privado**: no hay `--auto`; unir solo con `gh pr checks` en verde y luego `gh pr merge --squash`.

## Hecho y verificado por Brayan (nov. 2026)
- 32/32 RF; v1.1.0 y v1.2.0 publicadas.
- Respaldo diario de Neon: secretos creados y flujo en verde (RNF-15).
- Correos reales por Mailjet: llegan al ciudadano al confirmar, al ser rescatado y al ingresar al refugio.
- UptimeRobot vigila la página cada 5 min (no se duerme); sondeo de GitHub cada 30 min.
- PWA: grabar video con la cámara o elegir de la galería (≤ 60 s, ≤ 50 MB).
- Historial del veterinario (#218), «Mis rescates» del rescatista (#220) y hora de llegada (#222).
- Póster de Ingeniería de Software II terminado.

## Hecho el 5 de noviembre de 2026 (segunda sesión autónoma)

| Tarea | PR | Resultado |
|---|---|---|
| 1. Modo piloto (RNF-06) | #259, #264, #261, #262, #263 | Pestaña **Modo piloto** del administrador: «Nuevo participante» abre la PWA en modo prueba (P01, P02…, token de un solo uso, 24 h). El reporte de prueba se valida como uno real pero **no se guarda** (nunca llega a la cola ni a los rescatistas). Cronómetro del primer toque al código, SUS de 10 frases en el celular, resultados anónimos y **CSV** compatible con `resultados_piloto.py`. Tabla `piloto` (migración `0033`). Prueba e2e `e2e/piloto.spec.mjs`. Guía en `docs/aprende/piloto.md` |
| 2a. DT-12 | #266 | Historial del veterinario en 3 consultas (`buscar_varios`) e índices en `decisiones_triaje`, `descartes` y `rescates` (migración `0034`) |
| 2b. DT-13 | #268, #269, #270, #271, #274, #275, #276, #277 | `crear_app` partido en un router por módulo (`app/api/rutas_*.py`) con un `Contexto`; `main.py` 1 487 → ~470 líneas. Contrato intacto: el catálogo generado salió igual en cada paso y `tests/test_rutas_unicas.py` impide rutas duplicadas (detectó un `include_router` repetido en el camino) |
| 3. Pruebas de mutación | #273 | mutmut 3 en WSL2: 1 352 mutantes, 837 s (fuera del CI). Puntaje 90,5 % → **94,2 %**. `tests/test_mutacion.py` cubre la regla del patio (RN-05), el empate texto/video (RN-07), el rescate ajeno y el escalamiento con varios casos. `scripts/operacion/mutacion.sh` |
| 4. A-04 / DT-11 | #279 | La guía de Render no es concluyente: **comportamiento por defecto sin cambios**. Ajustes `PATITAS_ENCABEZADO_IP` y `PATITAS_PROXIES_CONFIANZA` y `GET /admin/diagnostico/ip` (solo administrador) para verificarlo y activarlo (P-17) |

Números de la suite al cerrar (CI de `main`, commit fabd054): **918 pytest, 97,49 % de
cobertura, 61 Vitest, 9 e2e, axe-core 56 revisiones sin fallas**.

## Hecho el 4 de noviembre de 2026 (sesión autónoma del asistente)

| Tarea | PR | Resultado |
|---|---|---|
| 0. Subir este archivo | #230 | Unido |
| 1. Revisar #224, #226 y #228 | — | Ya estaban unidos con sus pruebas («titkok», «Jsjsisoslqmwnabsnsnans», Node 24 / ubuntu-24.04): nada que hacer |
| 2. Vista previa del video | #232 | Diagnóstico de punta a punta: el nodo en WSL **sí** genera el MP4 (también en «no concluyente»), la API lo guarda, `tiene_vista` llega en true y el panel lo reproduce. Se corrigió lo que impedía verlo: un 4xx al subir la vista **tumbaba al nodo**; ahora el log dice siempre si la subió o por qué no, `--video` informa la vista (`--guardar-vista`), y el panel avisa si no carga y se actualiza cada 15 s mientras se analiza |
| 3. Pruebas e2e con Playwright | #234 | 8 pruebas (PWA a 390 px → veterinario → rescatista → coordinador → historiales → seguimiento, más 401/403 y descripción sin sentido); job `e2e` en el CI con capturas si falla; guía `docs/aprende/e2e.md` |
| 4. Auditoría | #236, #238, #240, #242 | `docs/aprende/auditoria.md`: sin hallazgos altos. Medios corregidos: límites de tamaño (A-01), 20 reportes por IP cada 15 min (A-02) y consultas acotadas con índices (A-03, migración `0032`). DT-11 a DT-13 en `DEUDA_TECNICA.md` |
| 5. Documentación de tesis | #244, #246 | `docs/tesis/`: C4, E-R, diccionario de datos y catálogo de 67 endpoints **generados del código** (`python -m scripts.tesis.generar_docs`), plan y reporte de pruebas, trazabilidad al día (movida desde `docs/aprende/`) |
| 6. Sustentación | #248 | `docs/aprende/sustentacion.md`: 60 preguntas con archivo y recorrido de 5 minutos |
| Extra: análisis de errores de la IA | #249 | 80 textos estilo WhatsApp **escritos por el asistente** (+20 de control). Recall de crítica 0,76 → 1,00 corrigiendo el léxico («convulciones», «no rrespira», «atropeyado», «desmayada», «electrocutado», «sangra mucho»…). `docs/aprende/errores-ia-texto.md` |
| Extra: revisión responsive | #251, #253 | 126 combinaciones (360/768/1440 px, claro y oscuro): sin desbordes ni contraste bajo; objetivos táctiles a 44 px, mensajes sin «(RN-01)», tablas como tarjetas en el celular. axe-core: 54 revisiones, 0 fallas |
| Extra: capturas del manual | #255 | 21 capturas nuevas con PostgreSQL y datos demo (video con vista previa, historial, «Mis rescates», rescate en curso, código en el ingreso) y `docs/manual-usuario.md` paso a paso por rol |

Números de la suite al cerrar (CI de `main`, commit c863a0b): **885 pytest, 97,22 % de
cobertura, 58 Vitest, 8 e2e, axe-core 54 revisiones sin fallas**. (`docs/tesis/pruebas.md`
tiene los del mediodía: 864 pytest en ffde3c4.)

Para retomar en local: la base `patitas_e2e` (datos demo + un reporte con video) sirve para e2e
y capturas; los scripts de diagnóstico `scripts/accesibilidad/_*.mjs` no se suben.

## Lo que falló o no se pudo, y por qué
- **Ver la vista previa en producción**: no hay acceso a Neon ni a la ventana de Ubuntu de
  Brayan. Todo funciona en local; si sigue sin verse, mira el log del nodo (ahora dice
  `vista previa del trabajo N subida (… KB)` o el motivo). **Reinicia el nodo con Ctrl+C** tras
  copiar el código: el proceso viejo sigue con el código viejo.
- **WSL no alcanza la API de Windows** (firewall): la prueba de punta a punta subió el MP4 real
  de WSL desde Windows con el mismo `ClienteApi` del nodo.
- **Local en Windows**: el Control de aplicaciones bloquea la DLL de `psycopg-binary` y la de
  scikit-learn. Se usó la libpq de PostgreSQL 17 (`PSYCOPG_IMPL=python` y su `bin` en el PATH);
  la prueba que compara con scikit-learn solo corre en el CI.
- **A-04 (IP falsificable con `X-Forwarded-For`)**: la documentación de Render no dice cuántos
  proxies agregan entradas; quedó configurable y con diagnóstico, sin activar (P-17).
- **5-nov, mutmut**: no corre en Windows (necesita `fork`); en WSL, `mutmut` 3 no compiló con
  Python 3.14 (sin wheel de `libcst`) → se usó el Python 3.12 del nodo de video. Tres corridas
  fallaron por configuración (pruebas que leen el panel, `also_copy` que pisaba los mutantes) y
  la cuarta funcionó; el script final está en `scripts/operacion/mutacion.sh`.
- **5-nov, PR apilados**: borrar la rama base de un PR apilado **cierra** el PR de arriba (le
  pasó a #260; se reabrió como #264). Desde entonces: primero se cambia la base y después se
  borra la rama. La pila de DT-13 se reconstruyó sobre `main` con un script de traslado para
  evitar conflictos.

## Pendiente de código
1. P-16: decidir si el modelo de texto puede seguir subiendo a «crítica» textos tranquilos.
2. DT-11 restante: A-08 (peticiones *chunked*) y A-09 (KDF de la clave de datos), baja severidad.
3. Bajar la complejidad de `crear_app` (39, conserva `noqa: C901`) con una función `armar_repositorios`.

## Pendiente de Brayan (no es código)
- Copiar `servicios/video/` al nodo en WSL y **reiniciarlo**; enviar un video y mirar el log.
- Piloto con 10 personas (RNF-06): guía en `docs/aprende/piloto.md` (ahora con el modo
  piloto); luego correr `scripts/operacion/resultados_piloto.py` y actualizar trazabilidad y póster.
- Revisar las decisiones P-15 (límite de reportes por IP), P-16 y **P-17** (activar la IP real
  en Render con `/admin/diagnostico/ip`) en `docs/aprende/preguntas-para-brayan.md`.
- Hacer el piloto con el **Modo piloto** del panel (pestaña del administrador) y descargar el CSV.
- Antes de la sustentación: descartar en el panel los reportes de prueba sin sentido.
- Agregar al profesor como colaborador del repositorio.
