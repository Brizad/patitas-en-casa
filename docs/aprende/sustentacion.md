# Sustentación: 60 preguntas de jurado y recorrido de 5 minutos

Cada pregunta trae una respuesta corta para decir en voz alta y **dónde se ve en el código**.
Complementa `preguntas-sustentacion.md` (más larga) y `guion-demo.md`. Cifras al 4 de noviembre
de 2026 (`docs/tesis/pruebas.md`).

## Arquitectura por capa

1. **¿Qué arquitectura tiene?** Un monolito modular en capas: rutas HTTP → servicios con las
   reglas → repositorios. Cada servicio recibe sus repositorios por el constructor. — `app/api/main.py` (`crear_app`), `docs/tesis/c4.md`
2. **¿Qué hay en la capa de presentación?** Tres interfaces: la PWA ciudadana (HTML/JS sin
   dependencias), el panel del personal (React + TypeScript) y la página de inicio. Las sirve
   la misma API. — `app/pwa/`, `panel/src/`, `app/inicio/`
3. **¿Y en la capa de API?** FastAPI valida la entrada con Pydantic, exige el rol y traduce los
   errores del dominio a códigos HTTP. No tiene reglas de negocio. — `app/api/main.py`, `app/api/video.py`
4. **¿Dónde están las reglas de negocio?** En los servicios: `ServicioReportes` (RN-01),
   `ServicioTriaje` (RN-02, RN-03), `ServicioConfirmacion` (RN-06, RN-16), `ServicioRescates`
   (RN-08), `ServicioCupos` (RN-04). — `app/reportes/`, `app/triaje/`, `app/rescates/`, `app/cupos/`
5. **¿Qué es un repositorio y por qué hay dos de cada uno?** Un `Protocol` que esconde dónde se
   guardan los datos: uno en memoria para pruebas rápidas y otro en PostgreSQL. Las mismas
   pruebas de contrato corren sobre los dos. — `app/reportes/repositorio.py`, `tests/test_repositorio_contrato.py`
6. **¿Por qué un monolito y no microservicios?** Un equipo de una persona y un servidor gratis
   de 512 MB: los microservicios multiplicarían despliegues y fallas de red sin beneficio. Lo
   único que se separó fue el video, porque no cabe en memoria. — `servicios/video/`
7. **¿Cómo viaja un reporte?** PWA → `POST /reportes` → `ServicioReportes` valida RN-01 →
   `ServicioTriaje` sugiere prioridad → se guarda → aparece en `GET /cola` ordenado. — `app/reportes/servicio.py`, `ordenar_cola` en `app/triaje/servicio.py`
8. **¿Qué es el outbox?** Al confirmar se guardan los avisos como «pendientes» en la misma
   transacción; un procesador los envía después con reintentos. Si el correo falla, el aviso
   no se pierde. — `app/avisos/procesador.py`, `app/reportes/repositorio_postgres.py` (`confirmar`)
9. **¿Qué corre en segundo plano?** Tres revisiones periódicas: escalamiento de rescates sin
   aceptar, envío de avisos y limpieza de videos y vistas previas. — `crear_app` (tareas), `app/config.py`
10. **¿Cómo se mantiene ordenado el código?** Ruff con complejidad máxima 10 en el CI, nombres
    en español y un PR por cambio de 300 líneas o menos. — `pyproject.toml`, `.github/workflows/ci.yml`

## Inteligencia artificial de texto

11. **¿Qué modelo usa el triaje?** Dos piezas: reglas con un léxico validado (reglas-v0) y un
    modelo TF-IDF + regresión logística. La versión se guarda en cada reporte. — `app/triaje/clasificador.py`, `app/triaje/modelo.py`
12. **¿Por qué el modelo no usa scikit-learn en producción?** El modelo entrenado se exporta a
    JSON y el cálculo se repite en Python puro: cabe en los 512 MB de Render. Una prueba
    compara las probabilidades con las de scikit-learn. — `app/triaje/modelo.py`, `test_modelo_triaje.py`
13. **¿Con qué datos se entrenó?** Con datos **sintéticos** generados por un script; no hay aún
    reportes reales etiquetados por veterinarios. Lo decimos como limitación (DT-04). — `scripts/ia/`
14. **¿Por qué el modelo solo puede subir la prioridad?** Porque se entrenó con datos
    sintéticos: si las reglas ven un crítico sigue crítico; el modelo solo puede agravar. Así
    no baja el recall de «crítica». — `app/triaje/combinado.py`
15. **¿Qué es RN-02?** Si la confianza es menor de 0,6 y la prioridad es media o baja, el
    reporte va a «requiere revisión»: nunca se asigna baja automática con dudas. — `app/triaje/servicio.py`, `UMBRAL_CONFIANZA` en `app/config.py`
16. **¿Y si el clasificador se cae (RN-03)?** Si falla o tarda más de 10 s: prioridad alta,
    estado «sin clasificar» y revisión manual (falla segura). — `ServicioTriaje._falla_segura`
17. **¿Cómo explica sus sugerencias (RNF-09)?** Muestra las señales que encontró («detectó
    convulsión») y los términos que más empujaron al modelo; toda sugerencia crítica o alta
    trae al menos una evidencia (#224). — `app/triaje/combinado.py`, `panel/src/mensajes.ts`
18. **¿Cómo rechazan textos sin sentido?** RN-01 exige 20 caracteres, al menos 4 palabras y
    entre 30 % y 70 % de vocales: «Jsjsisoslqmwnabsnsnans» no pasa; «perro herido muy grave»
    sí. — `app/reportes/descripcion.py`, `tests/test_descripcion.py`

## Inteligencia artificial de video

19. **¿Dónde se analiza el video?** En un nodo local (WSL2) que pide trabajos a la API; Render
    gratis no tiene memoria para los modelos. Si el nodo está apagado, manda el texto. — `servicios/video/patitas_video/trabajador.py`
20. **¿Qué modelos usa?** MediaPipe Object Detector (EfficientDet-Lite0) para encontrar al perro
    o gato y DeepLabCut SuperAnimal-Quadruped para 39 puntos del cuerpo. — `servicios/video/patitas_video/adaptadores.py`
21. **¿Por qué no MediaPipe Pose?** Solo conoce el cuerpo humano (33 puntos de una persona). — `adaptadores.py` (encabezado)
22. **¿Qué mide de la marcha?** Si está de pie, la asimetría entre patas pareadas, qué pata no
    apoya, la regularidad del paso y el desplazamiento. — `servicios/video/patitas_video/marcha.py`
23. **¿Qué decide la prioridad del video?** Una red MLP pequeña (5 entradas, 8 ocultas, 4
    salidas) exportada a JSON, con dos reglas de seguridad: si no se pone de pie o no apoya una
    pata, nunca baja de «alta». — `servicios/video/patitas_video/clasificador.py`
24. **¿Qué pasa si texto y video no coinciden (RN-07, RF-19)?** Gana la prioridad más alta y la
    discrepancia se muestra al veterinario; nunca cambia lo que ya decidió una persona. — `app/triaje/video.py` (`fusionar`, `aplicar_video`)
25. **¿Qué es «no concluyente»?** Si no se ve un perro o gato en la mitad del video o el cuerpo
    no se ve el tiempo suficiente, el video no opina y manda el texto. — `servicios/video/patitas_video/analisis.py`
26. **¿Qué ve el veterinario?** Una vista previa de 480p con el esqueleto dibujado, que se borra
    a los 7 días o al cerrarse el reporte; el video original se borra al terminar el análisis.
    — `EscritorVistaFfmpeg`, `app/video/servicio.py`, `panel/src/VideoDelReporte.tsx`

## Seguridad

27. **¿Cómo se guardan las contraseñas?** Solo el hash Argon2id; nunca en logs. — `app/usuarios/`
28. **¿Cómo funciona el inicio de sesión?** OAuth2 con contraseña → JWT firmado (HS256) que vence
    en 30 min; el panel lo guarda solo en memoria. — `app/seguridad/tokens.py`, `panel/src/api.ts`
29. **¿Cómo se controla qué puede hacer cada rol?** `exigir_rol` en cada ruta: 401 sin sesión y
    403 con otro rol. Hay 6 roles. — `app/api/seguridad.py`, `docs/tesis/catalogo-endpoints.md`
30. **¿Cómo se frena la fuerza bruta?** 5 fallos por correo o 20 por IP en 15 min → 429 con
    `Retry-After` (DT-06). — `app/usuarios/intentos.py`
31. **¿Y el abuso del reporte público?** Descripción de 500 caracteres o menos, cuerpo de 1 MB o
    menos y 20 reportes por IP cada 15 min (auditoría A-01, A-02). — `limitar_cuerpo`, `contar_reporte` en `app/api/main.py`
32. **¿Cómo se protege la privacidad del ciudadano?** No necesita cuenta; el contacto es opcional,
    con autorización (Ley 1581) y se cifra con AES-256-GCM; la consulta por código solo muestra
    pasos y fechas (RN-14). — `app/seguridad/cifrado.py`, `app/reportes/seguimiento.py`
33. **¿Cómo se evita la inyección SQL?** Todo pasa por SQLAlchemy Core con parámetros; no hay SQL
    armado con texto del usuario. — `app/*/repositorio_postgres.py`, `docs/aprende/auditoria.md`
34. **¿Y el XSS?** La PWA pinta con `textContent`, React escapa, y la CSP prohíbe scripts en línea
    y de terceros. — `POLITICA_PWA` en `app/api/main.py`
35. **¿Qué hallazgo de seguridad sigue abierto?** A-04: la IP sale del primer `X-Forwarded-For`,
    que el cliente puede falsificar; no se arregló a ciegas porque podría bloquear a todos. — `docs/aprende/auditoria.md`, DT-11

## Base de datos

36. **¿Qué base usan?** PostgreSQL 18 en Neon (producción) y 17 en local y en el CI; 21 tablas. — `docs/tesis/er.md`
37. **¿Qué es una migración?** Un archivo de Alembic por cada cambio del esquema; producción se
    actualiza sola al arrancar (`alembic upgrade head`). Hay 32. — `migraciones/versions/`, `Dockerfile`
38. **¿Cómo se evita superar la capacidad del refugio (RN-04)?** Un `UPDATE ... WHERE ocupados <
    capacidad`: si dos ingresos llegan a la vez, solo uno gana; el otro recibe 409. — `app/cupos/repositorio_postgres.py`
39. **¿Cómo se garantiza un rescatista por rescate (RN-08)?** Índices únicos parciales: uno por
    reporte vigente y uno por rescatista activo. Lo garantiza la base, no solo el código. — `app/bd/esquema.py` (`uq_rescates_*`)
40. **¿Por qué la bitácora es inmutable?** Un disparador rechaza `UPDATE` y `DELETE` (RF-32). — migración `0020`, `app/bitacora/`
41. **¿Cómo se evitan reportes duplicados al reenviar sin conexión?** La PWA manda una
    `Idempotency-Key`; la columna es única y el reenvío devuelve el mismo código. — `guardar_con_clave` en `app/reportes/repositorio_postgres.py`
42. **¿Qué índices agregaron por rendimiento?** `estado` y `creado_en` de `reportes`, para que la
    cola no lea toda la historia (A-03). — migración `0032`

## Pruebas: caja blanca y caja negra

43. **¿Cuántas pruebas hay?** 864 de pytest (97,22 % de cobertura), 58 del panel con Vitest y 8
    de punta a punta con Playwright. — `docs/tesis/pruebas.md`
44. **¿Qué es una prueba de caja blanca aquí?** Una que conoce el código y recorre sus ramas y
    límites, por ejemplo el 30 % y 70 % exactos de vocales. — `tests/test_descripcion.py`
45. **¿Y una de caja negra?** Solo habla HTTP y mira la respuesta, sin saber cómo está hecho:
    por ejemplo, 403 si el veterinario intenta registrar un ingreso. — `tests/test_api.py`, `e2e/flujo.spec.mjs`
46. **¿Qué prueban las pruebas de punta a punta?** Un navegador real recorre ciudadano →
    veterinario → rescatista → coordinador → seguimiento sobre PostgreSQL. — `e2e/flujo.spec.mjs`, `docs/aprende/e2e.md`
47. **¿Cómo prueban PostgreSQL sin dañar datos?** Base aparte `patitas_test` que se vacía en cada
    prueba (`bd_limpia`); en el CI un contenedor temporal. — `tests/conftest.py`
48. **¿Cómo prueban la concurrencia?** Hilos que intentan ocupar el último cupo o el mismo
    rescate a la vez; solo uno debe ganar. — `tests/test_cupos_contrato.py`, `tests/test_rescates_contrato.py`
49. **¿Cómo prueban el video sin instalar 3 GB?** La lógica recibe las piezas pesadas por puertos
    y se prueba con dobles; los modelos reales corren en un flujo de humo aparte. — `tests/test_video_analisis.py`, `.github/workflows/video-humo.yml`
50. **¿Qué es una prueba de regresión?** Una que reproduce un error ya corregido para que no
    vuelva, como «le grabaron un titkok» (#224) o la vista previa (#231). — `tests/test_modelo_triaje.py`, `tests/test_video_trabajador.py`

## Despliegue y operación

51. **¿Cómo se despliega?** Render construye el `Dockerfile` desde `main` en cada merge; al
    arrancar aplica las migraciones. — `Dockerfile`, `render.yaml`
52. **¿Qué revisa el CI en cada PR?** gitleaks, Ruff, pytest con PostgreSQL y cobertura ≥ 70 %,
    pruebas y compilación del panel, axe-core y Lighthouse, y el job e2e. — `.github/workflows/ci.yml`
53. **¿Cómo se respalda la base?** Copia diaria con `pg_dump` 18, cifrada con AES-256 y con prueba
    de restauración (RNF-15). — `.github/workflows/respaldo.yml`
54. **¿Cómo saben si se cae?** Sondeo de GitHub cada 30 min y UptimeRobot cada 5 min. — `.github/workflows/sondeo.yml`
55. **¿Cómo salen los correos?** Por la API HTTPS de Mailjet, porque Render gratis bloquea SMTP. — `app/notificaciones/mailjet.py`

## Decisiones y limitaciones

56. **¿Qué no cumple todavía?** RNF-06 (prueba con 10 usuarios) y la validación de la IA con
    datos de veterinarios (RNF-03 con datos reales). — `docs/tesis/trazabilidad.md`
57. **¿Por qué el video no se guarda?** Minimización de datos (RNF-08) y el 1 GB de Neon: se
    borra al analizarlo; solo queda una vista previa liviana 7 días. — `app/video/servicio.py`
58. **¿Qué tan bueno es el modelo de texto con textos reales?** No lo sabemos aún: con 80 textos
    escritos por el asistente (no por veterinarios) medimos los errores; es una prueba, no una
    validación. — `docs/aprende/errores-ia-texto.md`
59. **¿Qué harían con más presupuesto?** Plan pagado (sin dormirse, RNF-04), un servidor con GPU
    para el video y un conjunto real etiquetado por veterinarios para reentrenar. — `DEUDA_TECNICA.md`
60. **¿Qué aprendieron del proceso?** Que las reglas críticas deben vivir también en la base, que
    una falla debe ser segura y visible (RN-03, #231) y que un PR pequeño con pruebas se revisa
    y se defiende mejor. — `CHANGELOG.md`

## Recorrido de 5 minutos para la demo en vivo

Antes: abre https://patitas-en-casa-pnnk.onrender.com 10 minutos antes (despierta el servicio),
ten el panel en otra pestaña y la contraseña de demostración a mano. Si no hay internet, usa la
instancia local de `docs/aprende/e2e.md`.

| Minuto | Qué mostrar | Qué decir |
|--------|-------------|-----------|
| 0:00–1:00 | Teléfono (o el navegador a 390 px): `/app/`, escribe «Perro atropellado convulsionando en la avenida, sangra mucho», dirección y comuna; envía. Muestra el código | «Sin cuenta, con o sin conexión. La descripción sin sentido se rechaza (RN-01).» |
| 1:00–2:00 | Panel como **veterinaria**: abre el reporte en la cola, señala la prioridad sugerida, la confianza y las evidencias; confirma crítica | «La IA sugiere y explica; decide la persona (RN-06). Si ajusto, exige justificación (RN-16).» |
| 2:00–3:00 | Panel como **rescatista**: la oferta aparece; acepta, «Llegué al sitio» y «Trasladado al refugio» | «Un rescate, un rescatista: lo garantiza la base (RN-08).» |
| 3:00–4:00 | Panel como **coordinador**: registra el ingreso con el código; muestra la ocupación | «El cupo se toma con un UPDATE condicional (RN-04); al 90 % avisa.» |
| 4:00–4:40 | De vuelta en el teléfono: «Ver estado» con el código | «El ciudadano ve los pasos y nada privado (RN-14).» |
| 4:40–5:00 | GitHub: el último CI en verde (pytest, e2e, accesibilidad) | «Cada cambio pasa 864 pruebas, la de punta a punta y axe-core antes de unirse.» |

Si preguntan por el video: abre en la cola un reporte con video y muestra el análisis y la
vista previa (requiere el nodo encendido; si no, explica la falla segura).
