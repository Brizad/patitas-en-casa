# Auditoría de seguridad, calidad y rendimiento (4 de noviembre de 2026)

Revisión hecha por el asistente sobre `main` (después de #234), leyendo el código, las rutas
reales de la app (introspección de `crear_app`) y las pruebas. **No** es una prueba de
penetración ni sustituye el análisis de OWASP ZAP (`.github/workflows/zap.yml`).

Escala de severidad: **alta** = se puede explotar hoy y expone datos o deja el sistema caído;
**media** = abuso posible o degradación con el uso, con impacto limitado; **baja** = mejora de
higiene o de mantenimiento. **Info** = revisado y sin hallazgo.

## Resumen

| ID | Severidad | Hallazgo | Estado |
|----|-----------|----------|--------|
| A-01 | Media | `POST /reportes` (público) sin tope de descripción ni dirección; ningún cuerpo JSON limitado | Corregido en #236 |
| A-02 | Media | `POST /reportes` sin límite por IP: un robot llena la cola del veterinario | Corregido en #238 |
| A-03 | Media | `/cola`, `/rescates/ofertas` y el escalamiento periódico leen toda la historia de reportes | Corregido en #240 |
| A-04 | Media | La IP del cliente se puede falsificar con `X-Forwarded-For` | **Listo para activar** (#278): ajuste configurable y diagnóstico; falta verificar en Render (P-17) |
| A-05 | Baja | `GET /veterinario/historial` hace una consulta por fila (N+1) | DT-12 |
| A-06 | Baja | Sin índices para los historiales (`decisiones_triaje.veterinario`, `descartes.veterinario`, `rescates.rescatista`) | DT-12 |
| A-07 | Baja | `crear_app` mide 1 011 líneas (`noqa: C901`) | DT-13 |
| A-08 | Baja | El tope de 1 MB no cubre peticiones *chunked* sin `Content-Length` | Corregido (#283) |
| A-09 | Baja | La clave de datos se deriva con un SHA-256 simple (sin sal ni KDF lento) | Listo para activar (#284) |
| A-10 | Baja | Código repetido: la IP del cliente se lee igual en 3 lugares; `urlTira`/`urlVista` del panel son casi iguales | DT-13 |

No se encontraron hallazgos de severidad **alta**.

## Hallazgos

### A-01 · Media · Límites de tamaño (corregido, #236)
- **Evidencia:** `ReporteEntrada.descripcion: str` y `direccion: str | None` sin `max_length`
  en `app/api/main.py`; la columna es `Text` (`app/bd/esquema.py`). La PWA limita a 500 y 200
  (`app/pwa/index.html`), pero cualquiera puede llamar a la API directo. FastAPI lee el cuerpo
  entero antes de validar: un JSON de 100 MB ocupa la memoria de Render (512 MB).
- **Corrección:** topes en Pydantic (422) y middleware `limitar_cuerpo` (413 si
  `Content-Length` > 1 MB, salvo video, vista previa y fotos). Pruebas en
  `tests/test_limites_tamano.py`.

### A-02 · Media · Reportes sin límite por IP (corregido, #238)
- **Evidencia:** `crear_reporte` no consultaba `LimiteIntentos`; el registro de adoptantes sí
  (DT-09). OWASP API4 (consumo de recursos sin límite).
- **Corrección:** 20 reportes nuevos por IP en 15 min → 429 con `Retry-After`; los reenvíos con
  la misma `Idempotency-Key` no cuentan. Decisión P-15 en `preguntas-para-brayan.md`. Pruebas en
  `tests/test_limite_reportes.py`.

### A-03 · Media · Consultas sin acotar (corregido, #240)
- **Evidencia:** `repositorio.todos()` en `GET /cola`, en `ServicioRescates.ofertas` y en
  `escalar_vencidos`, que corre cada `REVISION_ESCALAMIENTOS_SEGUNDOS`. Además
  `posibles_duplicados(r, todos)` compara cada pendiente con todos los reportes (O(n·m)) y
  `reportes` no tenía índice en `estado` ni en `creado_en`.
- **Corrección:** `pendientes()`, `creados_desde()` y `confirmados_de_rescate()` filtran en
  PostgreSQL; migración `0032` con los dos índices. Pruebas en `tests/test_consultas_acotadas.py`
  (una falla si alguien vuelve a llamar a `todos()`).

### A-04 · Media · IP falsificable con `X-Forwarded-For` (pendiente)
- **Evidencia:** el `Dockerfile` arranca uvicorn con `--proxy-headers --forwarded-allow-ips='*'`.
  Con `'*'`, uvicorn 0.37 toma el **primer** valor de `X-Forwarded-For`
  (`uvicorn/middleware/proxy_headers.py`, `get_trusted_client_host`), y ese valor lo escribe el
  cliente. Quien mande `X-Forwarded-For: 1.2.3.<n>` distinto en cada intento esquiva los límites
  por IP (DT-06 por IP, DT-09 y A-02). El límite por correo de DT-06 sigue protegiendo las
  cuentas.
- **Por qué no se corrigió hoy:** el arreglo correcto es leer el valor que agrega el proxy de
  Render (el último, o el de un encabezado propio de Render). Sin ver los encabezados reales de
  producción, un cambio equivocado haría que **todos** los usuarios compartan una sola «IP» y
  se bloqueen entre sí (registro: 5 cada 15 min para toda la ciudad).
- **Siguiente paso:** registrar una vez en producción (sin datos personales) qué trae
  `X-Forwarded-For` en una petición propia; con eso, tomar el último valor confiable. Anotado
  como DT-11.
- **Actualización (#278).** La documentación oficial de Render no es concluyente: su guía de
  FastAPI pide restringir `--forwarded-allow-ips` a las IP del balanceador (sin dar cuáles) y
  su guía de PocketBase dice que Cloudflare escribe `CF-Connecting-IP` en cada petición a un
  servicio web público y pisa lo que mande el cliente, y que Cloudflare **agrega** a
  `X-Forwarded-For` (la entrada de la izquierda la controla el cliente). Por eso
  `ip_del_cliente` (`app/api/comun.py`) acepta `PATITAS_ENCABEZADO_IP` y
  `PATITAS_PROXIES_CONFIANZA` (N desde la derecha), **sin cambiar el comportamiento por
  defecto**, y `GET /admin/diagnostico/ip` (solo administrador) muestra los encabezados de proxy
  para elegir el valor con datos reales (P-17).

### A-05 · Baja · N+1 en el historial del veterinario
- **Evidencia:** `historial_del_veterinario` llama a `repositorio.buscar(codigo)` por cada
  decisión y dos veces por cada descarte. Con 200 decisiones son ~400 consultas. Cada
  veterinario ve solo lo suyo, así que crece despacio.
- **Arreglo propuesto:** `repositorio.buscar_varios(codigos)` con un `WHERE codigo IN (...)`.

### A-06 · Baja · Índices para los historiales
- **Evidencia:** `decisiones_de` filtra `decisiones_triaje.veterinario`, `descartes_de` filtra
  `descartes.veterinario` y `historial_de` filtra `rescates.rescatista`; ninguno tiene índice
  (los de `rescates` son parciales y solo cubren los activos). Tablas aún pequeñas.

### A-07 · Baja · Calidad: funciones largas
- **Evidencia:** `crear_app` (1 011 líneas, `app/api/main.py`) y `crear_rutas_video` (100 líneas)
  necesitan `noqa: C901`. Cada ruta por separado es sencilla, pero el archivo de 1 450 líneas
  cuesta de leer y de revisar.
- **Arreglo propuesto:** un `APIRouter` por módulo (`reportes`, `rescates`, `refugio`,
  `adopciones`, `admin`), como ya se hizo con el video.

### A-08 · Baja · Peticiones *chunked*
- **Evidencia:** `limitar_cuerpo` mira `Content-Length`. Una petición con
  `Transfer-Encoding: chunked` no lo trae. Los navegadores y la PWA siempre lo mandan.
- **Arreglo (#283):** `LimiteCuerpoSinLargo` cuenta los bytes a medida que llegan y, al pasar
  1 MB, responde 413 sin leer el resto. Pruebas en `tests/test_limites_tamano.py`.

### A-09 · Baja · Derivación de la clave de datos
- **Evidencia:** `Cifrador` usa `hashlib.sha256(clave)` como clave AES-256
  (`app/seguridad/cifrado.py`). Con una clave aleatoria de 32+ caracteres (lo que pide
  `.env.example`) es suficiente; con una frase humana sería débil frente a fuerza bruta.
- **Arreglo (#284):** con `PATITAS_CLAVE_KDF=scrypt` lo nuevo se cifra con una clave derivada
  por scrypt (n = 2^14, sal fija de la aplicación) y lleva el prefijo `v2:`; lo viejo se sigue
  leyendo con la clave v1 y los dos formatos se leen siempre, así que apagarlo no deja nada
  ilegible. Por defecto queda `sha256`: la clave de Render es aleatoria (`generateValue`).

### A-10 · Baja · Código repetido
- **Evidencia:** `peticion.client.host if peticion.client else "desconocida"` en tres rutas
  de `app/api/main.py`; `urlTira` y `urlVista` (`panel/src/apiVideo.ts`) son la misma función
  con otra ruta. Al arreglar A-04 conviene una sola función `ip_del_cliente`.

## Revisado sin hallazgos (info)

| Tema | Qué se revisó | Resultado |
|------|---------------|-----------|
| A01 Control de acceso | Las 58 rutas de `crear_app` más las 9 del video (tabla abajo) | Toda ruta no pública exige sesión y rol con `exigir_rol`; 401 sin sesión y 403 con otro rol (pruebas de API y e2e). El PDF de compromiso y la ficha clínica filtran por dueño o refugio: sin IDOR. |
| A02 Criptografía | `app/seguridad/` | Contraseñas con Argon2id; JWT HS256 con algoritmo fijo (`algorithms=[ALGORITMO]`), emisor y `exp` obligatorios, 30 min; contacto y perfil con AES-256-GCM y nonce aleatorio de 12 bytes. |
| A03 Inyección SQL | `grep` de `text(` y `execute(f` en `app/` | Todo pasa por SQLAlchemy Core con parámetros; `text()` solo en valores fijos del esquema. |
| A03 XSS | PWA, inicio y panel | La PWA pinta con `textContent` (nunca `innerHTML`); React escapa; sin `dangerouslySetInnerHTML`. |
| A05 Configuración | Cabeceras | CSP sin `unsafe-inline` ni terceros (`frame-ancestors 'none'`, `base-uri 'none'`), HSTS, `nosniff`, COOP, `Referrer-Policy: no-referrer` y `Permissions-Policy` (cámara y GPS solo del sitio, sin micrófono). Sin CORS: todo es del mismo origen. |
| A07 Autenticación | `POST /auth/token` | Límite por correo e IP (DT-06), token solo en memoria del panel (nunca `localStorage`). |
| A08 Integridad | CI | gitleaks sobre todo el historial con auto-prueba; acciones con versión fija. |
| A09 Registro | Bitácora (RF-32) | Toda escritura queda con actor y plantilla de la ruta, sin cuerpos ni tokens. |
| Secretos | Repositorio y `.env.example` | Solo valores de ejemplo; claves de demo y de pruebas aleatorias en el CI. |

## Control de acceso y validación por endpoint (OWASP)

| Método | Ruta | Quién (A01/A07) | Entrada y abuso (A03/A04) |
|---|---|---|---|
| POST | `/auth/token` | público | Formulario OAuth2; Argon2id; DT-06: 5 fallos por correo y 20 por IP en 15 min → 429 |
| GET | `/auth/yo` | cualquier sesión | Sin cuerpo |
| GET | `/admin/usuarios` | administrador | Sin cuerpo |
| POST | `/admin/usuarios` | administrador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| PUT | `/admin/usuarios/{correo}/activo` | administrador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/admin/usuarios/{correo}/accesos` | administrador | Sin cuerpo |
| GET | `/admin/refugios` | administrador | Sin cuerpo |
| POST | `/admin/refugios` | administrador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| PUT | `/admin/usuarios/{correo}/refugio` | administrador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/adoptantes` | público | Pydantic con topes; DT-09: 5 por IP en 15 min; misma respuesta si el correo existe |
| GET | `/adoptantes/yo/perfil` | adoptante | Sin cuerpo |
| PUT | `/adoptantes/yo/perfil` | adoptante | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/refugio/animales/{animal_id}/publicacion` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/adopciones/animales` | público | Solo publicados |
| GET | `/adopciones/animales/{animal_id}/foto` | público | `nosniff`; tipo verificado al subir |
| POST | `/refugio/animales/{animal_id}/foto` | coordinador | Lee ≤ 300 KB; JPEG/PNG/WebP por firma; 404 si el animal no es de su refugio |
| GET | `/adopciones/recomendaciones` | adoptante | Sin cuerpo |
| POST | `/adopciones/solicitudes` | adoptante | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/adopciones/solicitudes/mias` | adoptante | Sin cuerpo |
| GET | `/refugio/solicitudes` | coordinador | Sin cuerpo |
| GET | `/refugio/jornada/propuesta` | coordinador | Sin cuerpo |
| POST | `/refugio/solicitudes/{solicitud_id}/decision` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/refugio/solicitudes/{solicitud_id}/visita` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/refugio/solicitudes/{solicitud_id}/devolucion` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/refugio/seguimientos` | coordinador | Sin cuerpo |
| POST | `/refugio/seguimientos/{seguimiento_id}` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/adopciones/solicitudes/{solicitud_id}/compromiso.pdf` | adoptante, coordinador | 404 a quien no es el adoptante ni el coordinador del refugio (sin IDOR) |
| POST | `/reportes` | público | Pydantic: descripción ≤ 500 (A-01), dirección ≤ 200, comuna 1–10; A-02: 20 por IP en 15 min |
| GET | `/reportes/{codigo}` | público | Solo código y estado; códigos de 8 caracteres al azar |
| GET | `/reportes/{codigo}/seguimiento` | público | RN-14: solo pasos y fechas |
| GET | `/cola` | coordinador, veterinario | Sin cuerpo |
| POST | `/reportes/{codigo}/confirmacion` | veterinario | Justificación validada (RN-16, D-07); una sola vez |
| POST | `/reportes/{codigo}/descarte` | veterinario | Justificación validada; una sola vez |
| GET | `/reportes/{codigo}/avisos` | coordinador, veterinario | Sin cuerpo |
| GET | `/reportes/{codigo}/decisiones` | coordinador, veterinario | Sin cuerpo |
| GET | `/veterinario/historial` | veterinario | Sin cuerpo |
| PUT | `/rescatistas/yo/disponibilidad` | rescatista | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| PUT | `/rescatistas/yo/zona` | rescatista | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/rescatistas/yo` | rescatista | Sin cuerpo |
| GET | `/rescates/ofertas` | rescatista | Sin cuerpo |
| GET | `/rescates/mio` | rescatista | Sin cuerpo |
| GET | `/rescates/historial` | rescatista | Sin cuerpo |
| POST | `/rescates/{codigo}/aceptar` | rescatista | RN-08: índices únicos parciales en la base |
| POST | `/rescates/{codigo}/llegue` | rescatista | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/rescates/{codigo}/liberar` | rescatista | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/rescates/{codigo}/resultado` | rescatista | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/indicadores` | administrador, alcaldia, coordinador | Sin cuerpo |
| GET | `/indicadores/reportes.csv` | administrador, alcaldia, coordinador | Anonimizado (RF-31) |
| GET | `/indicadores/fichas.csv` | administrador, alcaldia, coordinador | Sin cuerpo |
| GET | `/indicadores/resumen.pdf` | administrador, alcaldia, coordinador | Sin cuerpo |
| GET | `/bitacora` | administrador | Guarda la plantilla de la ruta, nunca el cuerpo |
| GET | `/` | público | HTML estático con CSP |
| POST | `/refugio/ingresos` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/refugio/animales` | coordinador, veterinario | Sin cuerpo |
| GET | `/refugio/animales/{animal_id}` | coordinador, veterinario | Filtrado por el refugio del usuario (`fichas_de`) |
| POST | `/refugio/animales/{animal_id}/historial` | veterinario | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| POST | `/refugio/animales/{animal_id}/egreso` | coordinador | Pydantic con topes de largo; cuerpo ≤ 1 MB (A-01) |
| GET | `/refugio/ocupacion` | coordinador, veterinario | Sin cuerpo |
| POST | `/reportes/{codigo}/video` | público, con la `Idempotency-Key` del reporte | ≤ 50 MB por partes; firma MP4/MOV/WebM; ventana de tiempo; una vez; cupo de pendientes |
| POST | `/video/trabajos/reclamar` | trabajador de video (`X-Video-Token`, `hmac.compare_digest`) | Sin cuerpo |
| GET | `/video/trabajos/{id_}/archivo` | trabajador de video | Solo trabajos en análisis |
| POST | `/video/trabajos/{id_}/vista` | trabajador de video | ≤ 5 MB; firma MP4 |
| POST | `/video/trabajos/{id_}/resultado` | trabajador de video | Pydantic; tira PNG ≤ 200 KB; ≥ 3 evidencias con prioridad |
| POST | `/video/trabajos/{id_}/fallo` | trabajador de video | Motivo ≤ 300 |
| GET | `/reportes/{codigo}/video` | coordinador, veterinario | Sin cuerpo |
| GET | `/reportes/{codigo}/video/tira.png` | coordinador, veterinario | `private, no-store` |
| GET | `/reportes/{codigo}/video/vista.mp4` | coordinador, veterinario | `private, no-store` |

Tabla sacada de las rutas reales de la app (roles leídos de cada `exigir_rol`), más las 9 rutas
del video (`app/api/video.py`). Para repetirla, ver el catálogo de endpoints en `docs/tesis/`.
