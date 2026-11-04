# Cambios

Formato basado en *Keep a Changelog*; versiones según SemVer.

## [Sin publicar]

### Agregado
- Pruebas de punta a punta (#233): `e2e/` con Playwright recorre en el navegador el flujo completo sobre una instancia real (API + PostgreSQL + panel compilado + PWA): reporte desde el teléfono (390 px), confirmación crítica, rescate, ingreso con código, historiales y seguimiento (RN-14), más los errores (descripción sin sentido, 401 y 403). Job `e2e` en el CI con capturas y trazas como artefacto si falla. Guía en `docs/aprende/e2e.md`.

### Cambiado
- CI: las acciones de todos los flujos suben a versiones con Node 24 (`checkout`, `setup-python`, `setup-node` y `upload-artifact` a v6) y `runs-on` queda fijo en `ubuntu-24.04` en lugar de `ubuntu-latest`. Sin cambios en la aplicación.

### Corregido
- Seguridad, auditoría A-01 (#235): `POST /reportes` (público) rechaza con 422 una descripción de más de 500 caracteres o una dirección de más de 200, los mismos topes que ya tenía la PWA. Cualquier petición con un cuerpo de más de 1 MB responde 413 antes de leerlo, salvo las subidas de video, vista previa y fotos, que tienen su propio límite. Sin migración.
- Vista previa del video (#231): diagnóstico de punta a punta (WSL + API local con PostgreSQL): el nodo sí genera el MP4 también con «no concluyente», la API lo guarda y `tiene_vista` llega en `true`. Se corrigen los puntos débiles: un rechazo de la vista con un 4xx distinto de 404/409/410 (413, 415, 403 de un proxy) ya no tumba al nodo ni frena el resultado; el log del nodo dice siempre si subió la vista (y su tamaño) o por qué no la hay (sin ffmpeg, ffmpeg falló, ningún cuadro legible); `--video` informa la vista y `--guardar-vista` la guarda. El panel avisa si la vista no carga o si el análisis no la trae, y vuelve a preguntar cada 15 s mientras el video se analiza. Sin migración.
- RN-01 (#225): ya no se aceptan descripciones sin sentido como «Jsjsisoslqmwnabsnsnans». La descripción necesita al menos 4 palabras de 2 letras o más y entre 30 % y 70 % de vocales (`app/reportes/descripcion.py`); «perro atropellado no se levanta y sangra» sigue pasando. La API responde 422 y la PWA muestra «Describe con palabras qué le pasa al animal.» (misma regla en `reportar.js`; el service worker sube a `patitas-pwa-v6`). Sin migración.
- RNF-09 (#223): «El perro se está muriendo, porque le grabaron un titkok» salía crítica con 100 % y «Sin evidencias». Causa: el modelo la subió a crítica solo por palabras vacías («se», «esta», «le»), que el filtro de evidencias (#187) descarta, y las reglas no conocían «muriendo». Ahora «muriendo» y «agoniz» son señales críticas del léxico, y toda sugerencia crítica o alta sin evidencia muestra que el modelo no reconoció un término clínico concreto. Sin migración.

### Agregado
- Hora de llegada del rescatista (#221): la columna nueva `rescates.llegada_en` (migración `0031`) se llena al pulsar «Llegué al sitio». `GET /rescates/historial` devuelve `llegada_en` (UTC, o `null`) y «Mis rescates» muestra la hora local en vez de «Sí/Aún no»; los rescates anteriores a la migración siguen mostrando «Sí» porque no se inventa una hora. Para actualizar: `alembic upgrade head`.
- «Mis rescates» del rescatista (#219): `GET /rescates/historial` (solo rescatista) y pestaña en el panel con los rescates que aceptó (código, fecha de aceptación en hora local, si llegó, resultado y estado actual), del más reciente al más viejo; los liberados no aparecen. No muestra descripción ni dirección. La pantalla anterior pasa a llamarse «Ofertas y rescate actual». El servidor no guarda la hora de llegada, solo si llegó. Sin migración.
- Historial del veterinario (#217): `GET /veterinario/historial` (solo veterinario) y pestaña «Historial» en el panel con lo que confirmó, ajustó o descartó (código, fecha en hora local, prioridad sugerida y final, justificación, estado actual), del más reciente al más viejo. Sale de `decisiones_triaje` y `descartes`; el repositorio gana `decisiones_de` y `descartes_de`. Sin migración.
- Vista previa del video para el veterinario (#214, parte 2 de 2; cambia RNF-08): `POST /video/trabajos/{id}/vista` (trabajador, MP4 ≤ 5 MB) y `GET /reportes/{codigo}/video/vista.mp4` (solo personal, `private, no-store`). Se guarda por trozos en la tabla nueva `vistas_trozos` (migración `0030`, también tres columnas en `analisis_video`) y se borra a los 7 días o cuando el reporte se cierra (rescate atendido o descartado), en la revisión periódica. El video original se sigue borrando al terminar. El panel muestra un reproductor bajo «Análisis de video». Para actualizar: `alembic upgrade head`.
- Nodo de video (#214, parte 1 de 2): tras analizar, genera una vista previa liviana para el veterinario (MP4 H.264, 480p, 10 fps, ≤ 5 MB, con el esqueleto de DeepLabCut dibujado) con ffmpeg y la sube a `POST /video/trabajos/{id}/vista` antes de entregar el resultado. Es opcional: si falla ffmpeg o la API no la acepta, el análisis sigue igual. Requiere `ffmpeg` en el nodo (`sudo apt install ffmpeg`). Decisión del autor que cambia RNF-08; la API y el panel llegan en la parte 2.
- PWA ciudadana (#212): el video se puede grabar con la cámara trasera dentro de la página (contador, tope de 60 s, vista previa y «Repetir»; sin MediaRecorder usa la cámara del teléfono) o elegir de la galería. Se valida duración (60 s) y tamaño (50 MB) antes de subir. `Permissions-Policy` ahora permite la cámara solo desde el propio sitio; el micrófono sigue bloqueado.
- Avisos al ciudadano por el outbox (#204): si dejó un correo y autorizó el contacto (RF-18), recibe un aviso cuando un rescatista registra el resultado «trasladado» o «atendido en el sitio» y cuando el animal ingresa al refugio. `POST /refugio/ingresos` acepta `reporte` (opcional) con el código. Los mensajes solo llevan el código (RN-14).
- Panel (#206): el formulario «Registrar ingreso» tiene el campo opcional «Código del reporte» y muestra el error si el código no existe (422).

### Cambiado
- Migración `0029`: la unicidad de `avisos` pasa a (reporte, destinatario, mensaje), para que un mismo destinatario reciba avisos distintos del mismo reporte. Para actualizar: `alembic upgrade head`.

### Cambiado
- `render.yaml` (#202): se quita el bloque `databases` de `patitas-bd`, que ya se borró en Render; la base real es la de Neon.

### Corregido
- Respaldo diario: `pg_dump` 17 fallaba contra Neon (servidor 18.6). `PG_VERSION` pasa a 18 en `respaldo.yml` (también la base temporal de la prueba de restauración) y las guías dicen PostgreSQL 18 para Neon.

## [1.2.0] - 2026-11-02
Video temporal en PostgreSQL, base en Neon, avisos por Mailjet y por el outbox, respaldo diario,
piloto de usabilidad y rediseño del panel, la PWA y la página de inicio. Para actualizar:
`alembic upgrade head` (migraciones `0026` a `0028`).

### Agregado
- Avisos de escalamiento por el outbox (DT-07, #199): al escalar un rescate sin aceptar (RF-23), el aviso al coordinador y a los rescatistas de otras zonas se guarda en `avisos` y lo envía el procesador con reintentos; antes se enviaba directo y se perdía si el correo fallaba. El aviso se guarda antes de marcar el escalamiento, así que un fallo entre los dos pasos se reintenta.
- Piloto de usabilidad (RNF-06, #197): plantilla CSV y cuestionario SUS en `docs/piloto/`, script `scripts/operacion/resultados_piloto.py` (% que reporta en ≤ 90 s, meta 80 %; SUS promedio, meta 70) con su prueba, y guía de la sesión en `docs/aprende/piloto.md`.
- Respaldo diario (RNF-15, P-07): flujo `respaldo.yml` con `pg_dump` de Neon, cifrado AES-256, prueba de restauración en una base temporal y artefacto de 14 días; sin los secretos `NEON_DATABASE_URL` y `RESPALDO_CLAVE` avisa y no falla. Guía y restauración en `docs/aprende/respaldo.md`.
- Avisos por correo con la API HTTPS de Mailjet (P-08): `NotificadorMailjet` se usa si están `PATITAS_MAILJET_API_KEY`, `PATITAS_MAILJET_SECRET_KEY` y `PATITAS_CORREO_REMITENTE` (Render gratis bloquea SMTP); si no, SMTP o el log. El outbox y los reintentos no cambian. Guía en `docs/aprende/correo-mailjet.md`.

### Corregido
- Evidencias del triaje de texto con sentido clínico (#186): se filtran palabras vacías del español («se», «bien», «no se»), pares sin contenido y lugares o tiempos; van primero las señales de las reglas y el modelo no las repite. Si no hay 3 evidencias útiles se muestran menos (antes se rellenaba). RNF-09 queda como «las evidencias que haya, siempre útiles» para el texto.

### Documentación
- Estado real de hoy en `docs/aprende/trazabilidad.md` (video funcionando con el nodo local, base en Neon, #186 a #188) y lista exacta de lo que falta del ERS, con responsable, en `docs/aprende/avance.md` (#190).

### Agregado
- Video temporal en PostgreSQL (#188): el video espera por trozos de 1 MB en la tabla `videos_trozos` (migración 0028) y ya no se pierde si Render se reinicia. Se borra al terminar el análisis o a las 6 horas (también los trozos huérfanos); 50 MB por video y a lo sumo 5 esperando (`MAX_VIDEOS_PENDIENTES`, 250 MB como máximo en los 1 GB de Neon); con el cupo lleno responde 503 y el reporte sigue con el texto. `VIDEO_DIR` mantiene el disco como opción. Falla segura sin cambios.
- Revisión por rol (#182): en Indicadores el acuerdo del veterinario nombra el modelo por lo que hace (no `reglas-v0+tfidf-lr-v1`); capturas del manual «antes» (`docs/manual/antes/`) y «después» (`docs/manual/`) y resumen del rediseño en `docs/aprende/avance.md`.
- Detalle del reporte entendible de un vistazo para el veterinario (#180): `GET /cola` trae `descripcion`, `ubicacion`, `creado_en` (UTC) y `video_segundos` (nunca el contacto). El panel muestra qué pasó, dónde (con «Abrir en Google Maps»), cuánto hace que se reportó, la sugerencia explicada en lenguaje sencillo («prioridad crítica con confianza alta (90 %), según reglas de urgencia y modelo de texto») sin nombres como `tfidf-lr-v1`, las evidencias como frases y el análisis de video con su estado en insignia y la tira de 3 imágenes en un marco con pie de foto. Sin video ya no se pide el análisis (desaparece el 404 en la consola).
- Administración y adopción con el sistema de diseño (#178): rol y estado de las cuentas como insignias (Activa / Suspendida), formularios de cuenta y de refugio en rejilla (el botón queda en su propia fila), tabla de cuentas con desplazamiento en celular, compatibilidad «93/100» y estado de las solicitudes con insignia, y animales recomendados como tarjetas.
- Indicadores legibles para la Alcaldía, la coordinación y la administración (#176): cifras clave en tarjetas, nombres en español sencillo («Clasificado por la IA», «Crítica», «Trasladado al refugio») en lugar de claves técnicas, prioridades con insignia, plurales correctos («1 perfil») y bitácora dentro de una caja con desplazamiento.
- Pantallas del coordinador con el sistema de diseño (#174): formularios de ingreso, publicación y foto en rejilla de dos columnas (`ds-form`), un estado vacío con explicación en solicitudes, adopciones aprobadas, seguimientos y animales del refugio, e insignias para «en el refugio», «egresó» y «vencido».
- Pantalla del rescatista con el sistema de diseño (#172): la zona por comunas son botones grandes que se marcan con ✓, las ofertas son tarjetas con borde de prioridad y «Mi rescate» trae el enlace «Abrir en Google Maps» (`enlaceMapa`: GPS o dirección en Cúcuta). En el sistema, las casillas se alinean con su texto.
- Panel del personal con el sistema de diseño (#170): barra de marca con el rol de la sesión, pestañas, inicio de sesión con logo, tarjetas, mensajes de error y éxito, estados vacíos, tablas e insignias de prioridad (crítica, alta, media y baja) compartidas con la página de inicio y la PWA. La pestaña activa conserva su contraste en modo oscuro al pasar el ratón.
- PWA ciudadana rediseñada (#168) con el sistema de diseño: cabecera de marca, pestañas con subrayado, formulario en tarjetas, botones de 44 px, código de seguimiento grande y línea de tiempo. El service worker (v4) guarda también `/diseno/sistema.css` para abrir sin señal. En el sistema, la regla base de los botones baja su especificidad para que las variantes (`ds-btn--pri`) siempre ganen.
- Página de inicio rediseñada (#166) con el sistema de diseño: portada de marca con la acción urgente primero, pasos numerados, roles en tarjetas y señales de confianza. axe y Lighthouse siguen en 100.
- Sistema de diseño único (#164, `app/diseno/sistema.css`, servido en `/diseno/sistema.css`): colores de marca y de prioridad (crítica, alta, media, baja) con modo oscuro, tipografía, escala de espaciado, botones, campos, tarjetas, pestañas, tablas, insignias, estados vacíos y mensajes de error, éxito, aviso e información. Los PR siguientes lo aplican por zona (inicio, PWA y cada pantalla del panel).
- Sección «Forma de trabajo eficiente» en `CLAUDE.md` (#160): flujo completo sin pedir confirmación, merge automático, pruebas locales acotadas y resumen corto.
- Manual de usuario (#156, `docs/manual-usuario.md`): qué hace cada rol (ciudadano, veterinario, rescatista, coordinador, adoptante, administrador y Alcaldía) en lenguaje sencillo, con 17 capturas de los datos de demostración. `scripts/accesibilidad/capturas.mjs` las vuelve a tomar solas.
- Migración a Neon preparada (#154): `POSTGRES_SSLMODE` opcional en la conexión (Neon exige TLS), `scripts/operacion/migrar_a_neon.py` (pide las dos direcciones sin mostrarlas, copia con `pg_dump`/`pg_restore` sin poner la contraseña en la línea de comandos, compara las filas de cada tabla e imprime las variables para Render) y la guía `docs/aprende/migrar-a-neon.md`. No se ejecutó contra Render ni Neon: necesita las cuentas de Brayan.
- Accesibilidad medida (RNF-11, #147): `scripts/accesibilidad/revisar.mjs` recorre la página de inicio, la PWA y cada pestaña de los 6 roles con axe-core 4.14 (WCAG 2.2 A/AA y buenas prácticas, en claro, oscuro y celular de 320 px) y Lighthouse 13.6 (puntaje mínimo 100), más el reflujo a 320 px. Corre en el CI con un servidor de demostración en memoria (`servidor_demo.py`, contraseña aleatoria por corrida). Informe en `docs/aprende/accesibilidad.md`.
- Página de inicio pública en la raíz del sitio (#145, `app/inicio/`): explica el problema en Cúcuta, el flujo reporte → IA de texto y video → veterinario → rescate → refugio → adopción, los siete roles y la tecnología, con botones grandes a «Reportar emergencia» (`/app/`), «Adoptar» (`/panel/#registro`, abre el registro de adoptante) y «Entrar como personal». Sin JavaScript, con la misma CSP de la PWA, una columna en celular y modo oscuro.
- Scripts del nodo de video para Ubuntu/WSL2 (#143): `servicios/video/instalar_nodo.sh` instala todo y `arrancar_nodo.sh` pide el token sin mostrarlo (opción de guardarlo con permisos 600). README con 3 pasos para quien nunca usó Linux y `.gitattributes` con fin de línea LF para los `.sh`.

### Seguridad
- Bitácora con valor anterior y nuevo (RNF-12, #149): columnas `valor_anterior` y `valor_nuevo` (migración `0027`) para confirmar o descartar un reporte, suspender o vincular una cuenta, decidir una solicitud, ingresos y egresos (ocupación antes y después) y el perfil del adoptante (solo los nombres de los campos que cambiaron, nunca sus valores). `GET /bitacora` los devuelve y el panel del administrador los muestra como «antes → después».
- Perfiles de adoptante cifrados (RNF-08, #149): con `PATITAS_CLAVE_DATOS` el perfil se guarda entero en `perfiles_adoptante.datos_cifrados` (AES-256-GCM, la misma clave del contacto del ciudadano) y las columnas en claro quedan vacías (migración `0026`). Los perfiles que ya existían se cifran solos al arrancar la API. Para actualizar: `alembic upgrade head`.
- DT-09 pagada (#149): `POST /adoptantes` admite 5 registros por IP cada 15 minutos (429 con `Retry-After`; cuentan también los intentos fallidos) y responde exactamente igual si el correo ya tenía cuenta (antes: 409, que revelaba quién está registrado). La cuenta existente no cambia. El panel muestra un mensaje que cubre los dos casos.

### Corregido
- `GET /reportes/{codigo}` acepta el código en minúsculas o con espacios («f2hw 5rtb»), igual que `/seguimiento`: usa `normalizar_codigo` en vez de solo pasar a mayúsculas (antes daba 404).

### Cambiado
- `render.yaml` (#184, P-11): las variables `POSTGRES_HOST`, `_PORT`, `_USER`, `_PASSWORD` y `_DB` ya no vienen de `patitas-bd` (`sync: false`) y se agrega `POSTGRES_SSLMODE` (`sync: false`) para la base en Neon. `patitas-bd` se conserva unos días como respaldo.
- Datos de demostración: la veterinaria también queda vinculada al refugio de demostración y ve sus fichas (#156).
- `revisar.mjs` espera a que cada pestaña cargue sus datos antes de medir (antes podía medir la pantalla vacía); el resultado sigue en 0 fallas (#156).
- Panel: el inicio de sesión y el registro de adoptante van dentro de `<main>`, y la barra con sesión tiene un título de nivel 1 (axe `landmark-one-main`, `region`, `page-has-heading-one`; Lighthouse pasó de 96 a 100) (#147).
- `GET /` muestra la página de inicio en vez de redirigir a la PWA (#145).

## [1.1.0] - 2026-10-29
Análisis de video con un trabajador local (#125, RF-03, RF-19, RNF-02, DT-10; PR #126 a
#142). Para actualizar: `alembic upgrade head` (migración `0025`) y `PATITAS_VIDEO_TOKEN` en el
entorno (Render lo genera con `render.yaml`); el trabajador se instala aparte
(`servicios/video/README.md`). El modelo del video usa datos **sintéticos**.

### Agregado
- Medidas de la marcha a partir de los puntos clave del animal (`servicios/video/patitas_video/marcha.py`): de pie, pata sin apoyo, asimetría (cojera), regularidad del paso y desplazamiento, cada una con su umbral documentado.
- Clasificador de la marcha (`servicios/video/patitas_video/clasificador.py`): red neuronal pequeña (MLP 5-8-4) entrenada con medidas **sintéticas** y leída del JSON con Python puro; al menos 3 evidencias en lenguaje claro y reglas de seguridad (sin apoyo o sin ponerse de pie nunca queda por debajo de alta). `entrenamiento/entrenar.py --datos` reentrena con medidas etiquetadas por veterinarios (DT-04).
- Trabajos de análisis de video (`app/video/`): estados pendiente → enviado → terminado / no concluyente / fallido y repositorio en memoria.
- Tabla `analisis_video` (migración `0025`) y repositorio en PostgreSQL: un trabajo por reporte, reclamo con `FOR UPDATE SKIP LOCKED`. `actualizar_triaje` en los repositorios de reportes: el resultado del video nunca deshace una confirmación o un descarte del veterinario.
- `ServicioVideo` (`app/video/servicio.py`): solo el teléfono que creó el reporte sube el video (su clave de idempotencia), dentro de 30 min y una vez; RN-07 y RF-19 al recibir el resultado; reintentos (3), reclamos vencidos (10 min) y falla segura: video perdido, no concluyente o sin analizar en 6 h ⇒ manda el texto. El video se borra siempre (RNF-08).
- `POST /reportes/{codigo}/video` (público, con la misma `Idempotency-Key` del reporte): el video se escribe por partes en el disco temporal (≤ 50 MB, MP4/MOV/WebM por su firma) y responde «Video recibido, se está analizando». `GET /reportes/{codigo}/video` y `/video/tira.png` para el personal. Sin `PATITAS_VIDEO_TOKEN` el video está apagado (503) y manda el texto; `render.yaml` lo genera.
- Rutas del trabajador local con `X-Video-Token`: `POST /video/trabajos/reclamar` (204 sin trabajos), `GET /video/trabajos/{id}/archivo`, `POST .../resultado` (≥ 3 evidencias, tira PNG ≤ 200 KB) y `POST .../fallo`. La bitácora registra al «trabajador de video» y no cada sondeo vacío.
- Trabajador local (`servicios/video/patitas_video/trabajador.py` y `cliente.py`): pide trabajos a Render (no abre puertos), descarga el video por partes a una carpeta temporal que se borra siempre, entrega el resultado o informa el fallo, y espera cada vez más (hasta 5 min) si Render no responde. El token nunca se imprime.
- Tubería del análisis (`servicios/video/patitas_video/analisis.py`): 5 cuadros por segundo, perro o gato por cuadro, puntos del cuerpo, marcha y clasificador, con puertos para OpenCV, MediaPipe y DeepLabCut. Sin perro o gato en la mitad del video, o con el cuerpo mal visto, el resultado es «no concluyente».
- Adaptadores reales del trabajador (`adaptadores.py`): OpenCV (cuadros), MediaPipe Object Detector EfficientDet-Lite0 (perro o gato; MediaPipe Pose no sirve porque solo conoce personas), DeepLabCut SuperAnimal-Quadruped HRNet-w32 (39 puntos; pesos de uso académico, no se suben al repositorio) y la tira PNG ≤ 190 KB. `servicios/video/README.md` (instalación en WSL2: el Control inteligente de aplicaciones de Windows bloquea DLL de torchvision) y flujo manual «Video: prueba de humo».

## [1.0.0] - 2026-10-29
Plan autónomo de cierre: incremento 3 y fases 1 a 5, más las brechas del ERS (PR #108 a
#122). Publicada en https://patitas-en-casa-pnnk.onrender.com. Para actualizar una instalación:
`alembic upgrade head` (migraciones `0009` a `0024`) y, en el `.env` o en Render,
`PATITAS_ADMIN_CORREO` y `PATITAS_ADMIN_CONTRASENA` (primera cuenta de administración),
`PATITAS_CLAVE_DATOS` (cifrado del contacto) y, si se quiere, `PATITAS_DEMO_ACTIVA` y
`PATITAS_DEMO_CONTRASENA` (datos de demostración). El modelo de triaje se entrenó con datos **sintéticos** (ver
`docs/aprende/fase-4-ia.md`).

### Agregado
- Prueba de punta a punta (#121): cabeceras `Strict-Transport-Security`, `Permissions-Policy` y `Cross-Origin-Opener-Policy` en todas las respuestas (advertencias de OWASP ZAP) y compresión gzip. Panel: al elegir un reporte el foco va al detalle (en el celular quedaba debajo de la lista) y los botones de nombre de animal miden al menos 24 px (WCAG 2.2, RNF-11).
- RF-30, RF-31 y RNF-16 completos (#117): tiempo de respuesta por prioridad (hasta confirmar y hasta que un rescatista acepta), devoluciones, tasa de recomendación por tipo de hogar, y `GET /indicadores/fichas.csv` (fichas del refugio sin el texto de las notas).
- RF-25 (#115): foto de cada animal publicado (`POST /refugio/animales/{id}/foto`, coordinador; `GET /adopciones/animales/{id}/foto`, pública). JPEG, PNG o WebP de hasta 300 KB, validados por su contenido; se guardan en PostgreSQL porque el disco de Render gratis no persiste (migración `0024`). El catálogo trae `foto`. Panel: subir foto y verla en el catálogo.
- RF-27 y RF-10 (#113): el coordinador puede pedir una **visita previa** antes de decidir (`POST /refugio/solicitudes/{id}/visita`) y registrar una **devolución con su motivo** (`POST /refugio/solicitudes/{id}/devolucion`, RN-13): el animal reingresa (ocupa cupo; sin cupo responde 409 y no cambia nada) y vuelve al catálogo. Estados nuevos `visita` y `devuelta` (migración `0023`). Panel: botones en «Adopciones».
- RF-18 y RNF-08 (#111): contacto opcional del ciudadano (correo o teléfono) con autorización expresa, guardado con AES-256-GCM (`PATITAS_CLAVE_DATOS`, migración `0022`); si es un correo, recibe un aviso cuando un veterinario revisa su reporte, por el mismo outbox y con el destinatario cifrado también en la tabla de avisos. Campo nuevo en la PWA.
- Datos de demostración (#109): con `PATITAS_DEMO_ACTIVA=true` y `PATITAS_DEMO_CONTRASENA`, al arrancar se cargan una vez una cuenta por rol (`*@demo.patitas.co`), reportes en 7 comunas de Cúcuta, un rescate completo, una oferta abierta, cuatro animales con historial y tres en adopción. La contraseña nunca está en el código.
- Fase 5 (#102), cierre: bitácora general inmutable de toda acción que cambia datos, sin cuerpos ni datos personales, con un disparador que rechaza `UPDATE` y `DELETE` (`GET /bitacora`, migración `0020`, RF-32, RNF-12); indicadores sin datos personales (`GET /indicadores`, RF-30); exportar reportes en CSV y resumen en PDF anonimizados (`GET /indicadores/reportes.csv`, `GET /indicadores/resumen.pdf`, RF-31). Panel: pestaña «Indicadores».
- Fase 4 (#95), IA: clasificador TF-IDF + regresión logística entrenado con datos sintéticos (`scripts/ia/`), servido desde JSON en Python puro y combinado con las reglas (solo sube la prioridad; ≥ 3 evidencias; versión `reglas-v0+tfidf-lr-v1`; RF-02, RNF-03, RNF-09); compatibilidad adoptante–animal con puntaje, razones y alertas sin atributos protegidos (`GET /adopciones/recomendaciones`, RF-09, RNF-16); propuesta de asignación global en jornadas con el algoritmo húngaro (`GET /refugio/jornada/propuesta`, RF-28); fusión texto + video RN-07 y puerto del analizador (RF-19). Panel: recomendaciones y jornada.
- Fase 3 (#85), adopción: cuenta pública del adoptante con autorización de datos y perfil (`POST /adoptantes`, `GET/PUT /adoptantes/yo/perfil`, RF-08); publicar un animal y catálogo público (`POST /refugio/animales/{id}/publicacion`, `GET /adopciones/animales`, RF-25); solicitar (`POST /adopciones/solicitudes`, RN-10) y decidir (`POST /refugio/solicitudes/{id}/decision`) con restricciones duras (RN-05) y una adopción aprobada por animal (RN-11); aprobar da el egreso por adopción y programa los seguimientos a 30, 90 y 180 días (`GET/POST /refugio/seguimientos`, RF-10); compromiso de adopción en PDF sin dependencias (RF-29). Panel: registro y pantalla del adoptante; pestaña «Adopciones» del coordinador. Migraciones `0016` a `0019`.
- Fase 2 (#75), refugio completo: descartar un reporte falso o duplicado con justificación (`POST /reportes/{codigo}/descarte`, estado `descartado`, tabla `descartes`, D-02); posibles duplicados a ≤ 200 m y ≤ 2 h en la cola (RF-17); `version_modelo` en reportes y decisiones (RF-20, D-04); ficha clínica con historial que solo crece (`GET /refugio/animales`, `GET /refugio/animales/{id}`, `POST .../historial`, RF-06, RF-24); egresos que liberan el cupo (`POST .../egreso`, RF-26); ingresos y ocupación del refugio de cada persona. Panel: descartar, duplicados, fichas, historial, egresos, «Saltar a la cola» y foco tras confirmar (D-08). Migraciones `0012` a `0015`.
- Fase 1 (#67), pantallas por rol: rol `administrador` (migración `0010`) y primera cuenta creada al arrancar desde `PATITAS_ADMIN_CORREO` y `PATITAS_ADMIN_CONTRASENA` (sin reemplazar una existente). `GET/POST /admin/usuarios` y `PUT /admin/usuarios/{correo}/activo` (RF-16: suspender corta el acceso en la siguiente petición; nadie se suspende a sí mismo). `GET/POST /admin/refugios` y `PUT /admin/usuarios/{correo}/refugio` (RF-14, columna `usuarios.refugio_id`, migración `0011`). Panel: navegación por rol y pantallas del rescatista (disponibilidad, zona, ofertas, aceptar, llegué, resultado), del refugio (ocupación con nivel de alerta e ingresos del coordinador) y del administrador.
- Incremento 3 (II-03), outbox de avisos (#63, D-03 de II-01): al confirmar un crítico o alto, los avisos a los rescatistas de la comuna se guardan como **pendientes** en la misma transacción que la decisión (tabla `avisos`, migración `0009`) y un procesador los envía cada 15 s con reintentos (60 s, 120 s… hasta 1 h; 5 intentos) y estado real: enviado o fallido. Garantía «al menos una vez». `GET /reportes/{codigo}/avisos` (personal) muestra el estado, los intentos y el último error.
- Panel del personal en React (#64) en `/panel/`: inicio de sesión, cola priorizada con evidencias y confirmar o ajustar la prioridad con mensajes que no prometen de más («aviso pendiente de envío», nunca «se avisó»). Código en `panel/` (Vite + React + TypeScript); el CI compila y prueba el panel.
- Docker Compose (PostgreSQL 17 + API con el panel): `docker compose up --build`.
- Prueba de arquitectura: el núcleo (dominio, casos de uso, triaje, cupos, avisos) no importa FastAPI, SQLAlchemy, smtplib ni adaptadores.
- HU-08 y RF-12 (#61): pantalla "Reportar emergencia" de la PWA (descripción de 20 caracteres o más, GPS o dirección, comuna opcional) y pantalla del código de seguimiento con "Copiar código" y "Ver estado". Sin señal, el reporte se guarda en el teléfono (`localStorage`) y se reenvía al volver la conexión, al abrir la app y cada 30 s. `POST /reportes` acepta el encabezado opcional `Idempotency-Key`: el reenvío con la misma clave responde 200 con el mismo código y no crea otro reporte (columna única `clave_idempotencia`, migración `0008`). Sin el encabezado funciona como antes (343 pruebas).
- HU-08, parte 2 (#59, decisión del #47): PWA ciudadana en `/app/` (HTML, CSS y JavaScript sencillos con el diseño del prototipo, servida por la API) con la pantalla "Estado del reporte": código en minúsculas o con espacio, línea de tiempo y mensajes de código inexistente o sin conexión. Manifiesto instalable, service worker que guarda solo la interfaz (nunca respuestas de la API), modo oscuro y `Content-Security-Policy` estricta; `/` redirige a `/app/` (315 pruebas).
- HU-06, parte 2 (#57, decisión del #46): zona por comunas de Cúcuta (`comuna` opcional en el reporte, `PUT /rescatistas/yo/zona`, `GET /rescatistas/yo`), alerta por correo a los rescatistas disponibles de la comuna al confirmar un crítico o alto, y escalamiento: sin aceptar a los 15 min (crítico) o 30 min (alto) se avisa a los coordinadores una sola vez y el caso se ofrece en toda la ciudad. Migración `0007` (tabla `escalamientos`). Las ofertas muestran la comuna y si el caso está escalado (302 pruebas).

## [0.2.0] - 2026-10-15
Incremento 2, "Fundación segura". Para actualizar una instalación: `alembic upgrade head` (migraciones `0001` a `0006`) y completar el `.env` desde `.env.example` (`PATITAS_JWT_SECRETO`).

### Corregido
- BUG-02 (#16): la negación se detectaba por subcadena ("vecino", "camino", "pequeño") y degradaba casos críticos; ahora se compara la palabra anterior en cada aparición de la señal.
- BUG-03 (#17): dos clasificaciones colgadas agotaban el pool del triaje; al agotarse el tiempo se descarta el ejecutor y el error queda registrado con logging.
- BUG-04 (#18): dos ingresos simultáneos podían superar la capacidad del refugio; el cupo se comprueba y ocupa bajo un candado y `Refugio` valida 0 ≤ ocupados ≤ capacidad.
### Agregado
- Prueba del tiempo agotado del triaje (PA-02) y pruebas de regresión de BUG-02, BUG-03 y BUG-04 (40 pruebas, 97 % de cobertura).
- `CLAUDE.md` con el contexto del proyecto y las reglas de trabajo del incremento 2, y `.env.example` con las variables de PostgreSQL sin valores reales (#21).
- DT-01, paso 1 (#23): `app/ajustes.py` lee la conexión a PostgreSQL desde el entorno o `.env`; la contraseña no se imprime y, si falta, el error indica cómo completar el `.env`.
- DT-01, paso 2 (#25): pruebas de contrato de `RepositorioReportes`, parametrizadas por implementación (52 pruebas).
- DT-01, paso 3 (#27): `RepositorioPostgres` con SQLAlchemy y psycopg, tabla `reportes` creada por la migración de Alembic `0001` y CI con un servicio PostgreSQL 17 (79 pruebas).
- DT-01, paso 4 (#29): la API usa PostgreSQL al ejecutarse; los reportes sobreviven a un reinicio. Al arrancar se comprueba que la base esté en la última migración (83 pruebas).
- DT-05 (#30): los cupos del refugio y los animales ingresados se guardan en PostgreSQL (migración `0002`, que crea el refugio demo de 40 cupos). El cupo se toma con un `UPDATE` condicional, seguro aunque haya varios procesos (100 pruebas).
- Detección de secretos en el CI con gitleaks v8.30.1 sobre todo el historial, con una auto-prueba que confirma que un token falso sí se detecta (#33).
- DT-02, parte 1 (#35): cuentas de personal (veterinario, coordinador) con contraseñas Argon2id, tabla `usuarios` (migración `0003`) y comando `python -m app.usuarios.crear_usuario` (130 pruebas).
- DT-02, parte 2 (#37): inicio de sesión del personal con `POST /auth/token` (JWT HS256, 30 minutos) y `GET /auth/yo`. La clave de firma sale de `PATITAS_JWT_SECRETO` (149 pruebas).
- DT-03 (#12): la alerta de ocupación del 90 % (RN-04) se envía por correo SMTP a los coordinadores (`PATITAS_CORREOS_COORDINADORES`); sin SMTP configurado queda en el log. Una falla del correo no deshace el ingreso (167 pruebas).
- DT-06 (#41): `POST /auth/token` limita los intentos fallidos: 5 por correo o 20 por IP en 15 minutos; después responde 429 con `Retry-After`, incluso con la contraseña correcta. Los fallos se guardan en PostgreSQL (tabla `intentos_fallidos`, migración `0004`) y un inicio correcto reinicia el contador del correo (190 pruebas).
- HU-02 (#2): el veterinario confirma la prioridad sugerida o la ajusta con justificación de 10 caracteres o más (`POST /reportes/{codigo}/confirmacion`, RN-06, RN-16). La decisión queda en la bitácora `decisiones_triaje` (migración `0005`, `GET /reportes/{codigo}/decisiones`) y la base también exige la justificación (225 pruebas).
- HU-06, parte 1 (#50): rol rescatista, disponibilidad, ofertas de rescate (confirmados críticos o altos) y el ciclo aceptar → llegué al sitio → resultado, o liberar. RN-08 con índices únicos parciales en PostgreSQL (migración `0006`). La zona, el canal de alerta y el escalamiento esperan la decisión del #46 (256 pruebas).
- HU-08, parte 1 (#52): `GET /reportes/{codigo}/seguimiento`, línea de tiempo pública del reporte con la fecha del último cambio y sin datos personales (RN-14). Acepta el código en minúsculas o con espacios (266 pruebas).
### Cambiado
- D-06 (#75): todas las fechas de la API salen en UTC (`+00:00`); antes la bitácora salía con `-05:00`.
- D-07 (#75): la justificación de un ajuste o descarte exige además 5 letras como mínimo; «..........» se rechaza con 422.
- La respuesta de `POST /reportes/{codigo}/confirmacion` agrega el campo `avisos` (`programados` y `estado`: `pendiente`, `sin_destinatarios` o `no_aplica`). Cambio aditivo (#63). La confirmación ya no envía el correo en segundo plano: lo envía el procesador de avisos.
- `NotificadorCorreo.entregar()` lanza `EntregaFallida` si el SMTP falla; `enviar()` conserva el contrato anterior (registra y no propaga).
- `GET /cola` muestra solo los reportes pendientes de confirmar; los confirmados salen de la cola, como en el prototipo (HU-02, #2).
- **Incompatible:** `POST /refugio/ingresos` queda solo para el rol coordinador; un veterinario con sesión recibe 403 y el cupo no cambia. Así lo indica la pantalla P-06 "Registrar ingreso" del prototipo (#45). `GET /cola` y `GET /refugio/ocupacion` siguen para ambos roles (195 pruebas).
- **Incompatible:** `GET /cola`, `POST /refugio/ingresos` y `GET /refugio/ocupacion` exigen el encabezado `Authorization: Bearer <token>` de una cuenta de personal (401 sin sesión, 403 sin permiso). Se elimina `X-Rol` (DT-02, #40).
- La API se inicia con `uvicorn --factory app.api.main:crear_app`; `crear_app()` recibe el repositorio (las pruebas inyectan el de memoria) y el módulo ya no crea la app al importarse (#29).
### Deuda técnica
- DT-01 pagada (#10). DT-05 registrada y pagada (#30). DT-02 pagada (#11). DT-03 pagada (#12). Registrada y pagada DT-06 (#41): límite de intentos de inicio de sesión.

## [0.1.0] - 2026-09-29
### Agregado
- Registro de reportes de emergencia sin cuenta, con validaciones (RF-01, HU-01).
- Triaje por texto con clasificador de reglas v0, política de baja confianza y falla segura (RF-02, RNF-03).
- Cola priorizada con control de rol (RF-04, HU-02).
- Registro de ingresos, control de cupos y alerta al 90 % (RF-06, RF-07, HU-03).
- API REST con FastAPI y pipeline de CI (build, lint, test).
### Corregido
- BUG-01: señales con tilde no se detectaban en el triaje.
