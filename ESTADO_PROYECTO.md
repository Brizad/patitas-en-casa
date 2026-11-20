# Estado del proyecto Patitas en Casa (para retomar en cualquier sesión)

Lee primero `CLAUDE.md`, `docs/aprende/avance.md` y `git log --oneline -20`.
Producción: https://patitas-en-casa-pnnk.onrender.com (Render + Neon PostgreSQL 18 + Mailjet).
El repositorio es **público** (desde el cierre): no hay `--auto`; unir solo con `gh pr checks` en verde y luego `gh pr merge --squash`.

## Cierre: v1.3.0 (20 de noviembre de 2026)

Detalle de trabajos y bitácora en `PLAN_CIERRE.md`. Integrado: video con estado del nodo y
actualización automática (#332 a #336), RN-01 en la base (#342), H-1/H-2 y «despertando» (#344),
observabilidad (#349), escaneo de seguridad en el CI (#351), respaldo con alerta (#353), triaje con IA
documentado y reentrenable (#355), `rutas_reportes` y `rutas_adopciones` sin `noqa` (#357, #359),
ASVS nivel 1, caché/marcos y cambio de contraseña (#361 a #363), `/indicadores` sin N+1 (#365) y
cobertura mínima de 90 % (#367). Última corrida del CI de `main`: 1 093 pytest, 97,6 % de cobertura.
Pendiente: 5c (panel «despertando»), 4c (5 `noqa` restantes), 4d, 6b, 3b y, para después, 8b y 8c.

## Hecho y verificado por Brayan (nov. 2026)
- 32/32 RF; v1.1.0 y v1.2.0 publicadas.
- Respaldo diario de Neon: secretos creados y flujo en verde (RNF-15).
- Correos reales por Mailjet: llegan al ciudadano al confirmar, al ser rescatado y al ingresar al refugio.
- UptimeRobot vigila la página cada 5 min (no se duerme); sondeo de GitHub cada 30 min.
- PWA: grabar video con la cámara o elegir de la galería (≤ 60 s, ≤ 50 MB).
- Historial del veterinario (#218), «Mis rescates» del rescatista (#220) y hora de llegada (#222).
- Póster de Ingeniería de Software II terminado.

## Hecho el 5 de noviembre de 2026 (noche: rediseño visual)

Toda la interfaz con el sistema visual de `DESIGN.md` (crema, tinta, lavanda; EB Garamond y
Figtree locales; bordes de 2 px y radios grandes; sin sombras). Cambió la apariencia, no los
flujos ni las reglas RN. Guía con los valores reales: `docs/tesis/guia-estilo.md`.

| Tarea | PR | Resultado |
|---|---|---|
| Página de inicio y fuentes locales | #294, #295 | Fuentes OFL en `app/diseno/fuentes/` (44 KB); la CSP no cambia |
| Tokens compartidos | #297, #299 | `--pc-*` → `--ds-*` en `app/diseno/sistema.css`; gris de la referencia oscurecido a `#5c5c54` por contraste |
| PWA | #301 | Fuentes también sin señal (service worker) |
| Panel: estructura y cada rol | #305, #309, #311, #315, #318, #319 | Prioridad con forma ▲◆●○ y barra (no solo color, WCAG 1.4.1); tablas como tarjetas en el celular |
| Ilustraciones SVG propias | #320, #321 | Ícono de la app, 7 íconos por rol, portada y estados vacíos; SW `v10` |
| Correos HTML | #312 | `multipart/alternative` con el texto de siempre; sin imágenes ni rastreo; RN-14 y `html.escape` |
| Regresión visual | #322 | 16 capturas base (`e2e/capturas/`), 1 % de tolerancia, en el job `e2e` |
| Guía de estilo y sustentación | #323, #325 | Contrastes medidos; preguntas 61 a 70 y recorrido de 5 min con el diseño nuevo |
| Cierre | #327 | Manual con capturas nuevas y cifras del CI en `docs/tesis/pruebas.md` |

Números de la suite al cerrar (CI de `main`, commit 8094ad4, run 42021806974): **980 pytest,
97,48 % de cobertura, 68 Vitest, 25 e2e (9 del flujo + 16 de regresión visual), axe-core 56
revisiones sin fallas, Lighthouse 100 en las 4 pantallas públicas**.

## Hecho el 5 de noviembre de 2026 (tercera sesión autónoma: pendientes y preguntas)

| Tarea | PR | Resultado |
|---|---|---|
| Complejidad de `crear_app` | #286, #287, #288 | Repositorios en `app/api/armado.py`, middlewares y ciclo de vida en `app/api/middlewares.py`, avisos al ciudadano en `app/avisos/ciudadano.py`. Complejidad **41 → 8**, ya **sin** `noqa: C901`. Mismo contrato |
| A-08 / DT-11 | #289 | El tope de 1 MB también vale para peticiones *chunked* (`LimiteCuerpoSinLargo`, 413) |
| A-09 / DT-11 | #290 | `PATITAS_CLAVE_KDF=scrypt` cifra lo nuevo con clave derivada por scrypt (`v2:`) y sigue leyendo lo viejo. **Apagado** por defecto (P-18) |
| Preguntas para Brayan | #291 | P-16: `MODELO_SUBE_MAX_NIVELES` (medido: con tope el recall de crítica baja de 1,00 a 0,80–0,84; se recomienda dejarlo apagado). P-12: `AVISAR_REGISTRO_DUPLICADO` (aviso después de responder). Los dos **apagados** por defecto |

Números de la suite al cerrar (CI de `main`, commit 3da9b78): **932 pytest, 97,48 % de
cobertura, 61 Vitest, 9 e2e, axe-core 56 revisiones sin fallas**.

Fuera de la app: la skill **UI/UX Pro Max** (v2.15.0) quedó en `.claude/skills/` con
`uipro init --ai claude`. Esa carpeta no la sigue git.

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
- **5-nov (tercera sesión)**: nada falló dos veces. Los issues #282 a #285 no se cerraron solos
  porque los PR decían «Cierra #N» (GitHub solo entiende *Closes/Fixes*); se cerraron a mano.
- **5-nov (noche)**: los PR #314 y #317 estaban hechos sobre ramas viejas o apiladas y no se podía
  reescribir su rama (sin `push --force`); se rehicieron sobre `main` como #323 y #322 y los viejos
  se cerraron. La captura del análisis de video del manual no se retomó (necesita el nodo).

## Pendiente de código
Nada abierto. Queda listo para activar, si Brayan lo decide: P-12, P-16, P-17 (A-04) y P-18 (A-09).
DT-04 (validar el modelo con reportes reales) depende del piloto y de datos reales.

## Pendiente de Brayan (no es código)
- Copiar `servicios/video/` al nodo en WSL y **reiniciarlo**; enviar un video y mirar el log.
- Piloto con 10 personas (RNF-06): guía en `docs/aprende/piloto.md` (ahora con el modo
  piloto); luego correr `scripts/operacion/resultados_piloto.py` y actualizar trazabilidad y póster.
- Revisar las decisiones P-12, P-15, P-16, **P-17** (activar la IP real en Render con
  `/admin/diagnostico/ip`) y P-18 en `docs/aprende/preguntas-para-brayan.md`.
- Pegar en `CLAUDE.md` el texto sugerido de la regla 2 (P-01): el asistente no cambia sus
  propias reglas de permiso.
- Hacer el piloto con el **Modo piloto** del panel (pestaña del administrador) y descargar el CSV.
- Antes de la sustentación: descartar en el panel los reportes de prueba sin sentido.
- Agregar al profesor como colaborador del repositorio.
