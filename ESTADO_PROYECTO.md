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
- **A-04 (IP falsificable con `X-Forwarded-For`)**: no se corrigió a ciegas; podría bloquear a
  todos a la vez. Hay que ver una vez los encabezados reales de Render (DT-11).

## Pendiente de código
1. A-04 de la auditoría (DT-11), DT-12 (historiales N+1 e índices) y DT-13 (partir `crear_app`).
2. P-16: decidir si el modelo de texto puede seguir subiendo a «crítica» textos tranquilos.

## Pendiente de Brayan (no es código)
- Copiar `servicios/video/` al nodo en WSL y **reiniciarlo**; enviar un video y mirar el log.
- Piloto con 10 personas (RNF-06): guía en `docs/aprende/piloto.md`; luego correr
  `scripts/operacion/resultados_piloto.py` y actualizar trazabilidad y póster.
- Revisar las decisiones P-15 (límite de reportes por IP) y P-16 en `docs/aprende/preguntas-para-brayan.md`.
- Antes de la sustentación: descartar en el panel los reportes de prueba sin sentido.
- Agregar al profesor como colaborador del repositorio.
