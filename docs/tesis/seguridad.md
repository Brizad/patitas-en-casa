# Seguridad: OWASP ASVS 4.0.3, nivel 1, contra el código

Auditoría del 17 de noviembre de 2026 (#360). Se recorrieron los controles de **nivel 1** del
*Application Security Verification Standard* 4.0.3 y cada uno se contrastó con el código o con
producción. Complementa `docs/aprende/auditoria.md` (hallazgos A-01 a A-10 del 4 de noviembre).

**Cómo leer la tabla.** «Cumple» lleva el archivo o la prueba que lo demuestra. «No cumple»
se dice sin adornos y lleva qué se propone. «No aplica» explica por qué. Los números de control
son los de ASVS 4.0.3; antes de citarlos en un documento formal, cotéjalos con el estándar
publicado (se escribieron de memoria del estándar, no copiados de él).

**Qué no cubre.** No es una prueba de penetración: nadie atacó el sistema. No se revisó la
configuración de las cuentas de Render, Neon, Mailjet ni GitHub (contraseñas, MFA, quién tiene
acceso): eso es de Brayan. El nivel 1 es el mínimo de ASVS; no cubre los niveles 2 y 3.

## Resumen

Se cuentan las **filas** de las tablas de abajo; algunas agrupan varios controles vecinos que se resuelven con la misma evidencia.

| Capítulo | Cumple | Parcial | No cumple | No aplica |
|---|---|---|---|---|
| V2 Autenticación | 11 | 1 | 5 | 3 |
| V3 Sesiones | 6 | 1 | 0 | 1 |
| V4 Control de acceso | 6 | 0 | 1 | 1 |
| V5 Validación y codificación | 12 | 0 | 0 | 3 |
| V6 Criptografía | 1 | 0 | 0 | 0 |
| V7 Errores y registros | 2 | 1 | 0 | 0 |
| V8 Protección de datos | 5 | 1 | 1 | 0 |
| V9 Comunicaciones | 2 | 0 | 0 | 0 |
| V10 Código malicioso | 2 | 0 | 0 | 1 |
| V11 Lógica de negocio | 3 | 0 | 0 | 0 |
| V12 Archivos | 6 | 0 | 1 | 0 |
| V13 API | 5 | 0 | 0 | 1 |
| V14 Configuración | 14 | 0 | 0 | 0 |
| **Total** | **75** | **4** | **8** | **10** |

**Corregido en esta auditoría (con prueba que fallaba antes):**

| Control | Qué faltaba | PR |
|---|---|---|
| 2.1.5, 2.1.6 | Nadie podía cambiar su contraseña: la ponía el administrador y la seguía conociendo | #362 (`POST /auth/contrasena`) |
| 8.2.1 | Las respuestas JSON de la API no decían que no se guardaran en caché | #361 |
| 14.4.6, 14.4.7 | `Referrer-Policy` y la protección contra enmarcado solo estaban en la PWA y el panel | #361 |
| 4.1.x | No había una prueba que recorriera todas las rutas exigiendo sesión | `tests/test_acceso_por_defecto.py` |
| 14.2.1 | El CI no revisaba vulnerabilidades de las dependencias ni hacía análisis estático | #351 (`ci-security.yml`), #340 (cryptography 50.0.0) |
| Guía 13 | `/metrics` quedaba pública si se activaba sin token | #349 |

## V2 Autenticación

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 2.1.1 | Contraseñas de 12 caracteres o más | Cumple | `app/usuarios/contrasenas.py` (`MIN_CARACTERES = 12`), `tests/test_usuarios.py` |
| 2.1.2 | Se permiten 64 o más; tope ≤ 128 | Cumple | `MAX_CARACTERES = 128` |
| 2.1.3 | No se truncan | Cumple | Se hashea la cadena completa (`hashear`) |
| 2.1.4 | Cualquier carácter Unicode | Cumple | Sin filtro de caracteres en `validar_politica` |
| 2.1.5 | El usuario puede cambiar su contraseña | Cumple (desde #362) | `app/api/rutas_admin.py` (`cambiar_mi_contrasena`), `tests/test_cambiar_contrasena.py` |
| 2.1.6 | El cambio exige la actual y la nueva | Cumple (desde #362) | `ServicioUsuarios.cambiar_contrasena` |
| 2.1.7 | Se comparan con una lista de contraseñas filtradas | **No cumple** | No hay lista. Propuesta P-S1: lista local de las más comunes de 12 o más caracteres |
| 2.1.8 | Medidor de fortaleza | **No cumple** | El panel solo dice «12 caracteres o más». Propuesta P-S2 |
| 2.1.9 | Sin reglas de composición | Cumple | Solo se exige el largo |
| 2.1.10 | Sin rotación periódica obligatoria | Cumple | No existe caducidad de contraseñas |
| 2.1.11 | Se puede pegar la contraseña | Cumple | Campos `type="password"` normales en `panel/src/App.tsx` |
| 2.1.12 | Se puede ver la contraseña al escribirla | **No cumple** | No hay botón de mostrar. Propuesta P-S2 |
| 2.2.1 | Controles contra la fuerza bruta | Cumple | `app/usuarios/intentos.py`: 5 fallos por correo o 20 por IP en 15 min → 429; `tests/test_autenticacion.py` |
| 2.2.2 | Autenticadores débiles (SMS, correo) limitados | No aplica | No se usan como factor de autenticación |
| 2.2.3 | Aviso seguro al usuario cuando cambia su credencial | **No cumple** | El cambio de contraseña no envía correo. Propuesta P-S3 (usar el outbox de avisos) |
| 2.3.1 | Contraseñas iniciales aleatorias y que caducan | Parcial | La cuenta inicial sale de variables de entorno y no se reemplaza (`app/usuarios/admin_inicial.py`); las que crea el administrador no obligan a cambiarla en el primer ingreso. Propuesta P-S4 |
| 2.5.1 a 2.5.3, 2.5.6 | Recuperación de contraseña segura | No aplica | No existe «olvidé mi contraseña»: quien la pierde pide una cuenta nueva al administrador. Es una carencia de uso, no un canal inseguro |
| 2.5.4 | Sin cuentas por defecto o compartidas | Cumple | No hay cuentas en el código; las de demostración solo existen con `PATITAS_DEMO_ACTIVA` (`app/demo.py`) |
| 2.5.5 | Aviso si cambia un factor de autenticación | **No cumple** | Igual que 2.2.3 |
| 2.7.x, 2.8.1 | Códigos fuera de banda y de un solo uso | No aplica | No hay segundo factor |

## V3 Sesiones

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 3.1.1 | El token nunca va en la URL | Cumple | `Authorization: Bearer`; el token del piloto se quita de la barra al abrir (`app/pwa/piloto.js`) |
| 3.2.1 | Token nuevo en cada autenticación | Cumple | `EmisorTokens.emitir` (`app/seguridad/tokens.py`) |
| 3.2.2 | Al menos 64 bits de entropía | Cumple | JWT firmado con HS256 y un secreto de 32 caracteres o más (`MIN_CARACTERES_SECRETO_JWT`, `app/ajustes.py`) |
| 3.2.3 | El navegador guarda el token de forma segura | Cumple | Solo en memoria, nunca en `localStorage` (`panel/src/api.ts`); al recargar hay que entrar otra vez |
| 3.3.1 | Cerrar sesión invalida el token | Parcial | «Salir» borra el token del navegador, pero el JWT sigue siendo válido hasta 30 minutos: no hay lista de revocación. Riesgo aceptado por el tiempo corto |
| 3.3.2 | Reautenticación periódica | Cumple | El token vence a los 30 minutos y no se renueva solo |
| 3.4.1 a 3.4.5 | Atributos de las cookies de sesión | No aplica | No se usan cookies (comprobado: ningún `set_cookie` en `app/`) |
| 3.7.1 | Sesión válida antes de operaciones sensibles | Cumple | El cambio de contraseña pide además la actual (#362) |

## V4 Control de acceso

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 4.1.1 | Se aplica en el servidor | Cumple | `exigir_rol` en cada ruta (`app/api/seguridad.py`) |
| 4.1.2 | El usuario no puede manipular sus atributos | Cumple | El rol sale de la base en cada petición, no del token ni del cuerpo; `POST /adoptantes` siempre crea adoptante |
| 4.1.3 | Mínimo privilegio | Cumple | Roles separados: solo el veterinario confirma (RN-06), solo el coordinador ingresa, `/admin/*` solo administrador |
| 4.1.5 | Falla de forma segura | Cumple | Sin sesión, 401; con otro rol, 403. `tests/test_acceso_por_defecto.py` recorre todas las rutas |
| 4.2.1 | Sin acceso a objetos de otros (IDOR) | Cumple | El coordinador solo ve animales y solicitudes de su refugio (404 para los demás); el adoptante solo su perfil; el video solo con la clave de quien reportó |
| 4.2.2 | Protección contra CSRF | Cumple | Sin cookies: el token viaja en una cabecera que otro sitio no puede poner |
| 4.3.1 | Interfaces de administración con segundo factor | **No cumple** | No hay MFA. Propuesta P-S5 (TOTP para el rol administrador); queda como deuda |
| 4.3.2 | Sin listado de directorios | No aplica | `StaticFiles` no lista carpetas |

## V5 Validación, saneamiento y codificación

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 5.1.1 | Sin contaminación de parámetros | Cumple | FastAPI toma parámetros tipados y declarados |
| 5.1.2 | Sin asignación masiva | Cumple | Modelos Pydantic con campos explícitos; el rol, el estado y la prioridad nunca salen del cuerpo |
| 5.1.3 | Validación positiva de toda entrada | Cumple | Largos, rangos y enumeraciones en cada modelo (`app/api/rutas_*.py`); tope de 1 MB (`app/api/middlewares.py`) |
| 5.1.4 | Datos estructurados validados | Cumple | Comuna 1 a 10, coordenadas, código de 8 caracteres |
| 5.1.5 | Redirecciones solo a destinos permitidos | No aplica | La API no redirige a direcciones que dé el usuario |
| 5.2.1 a 5.2.3, 5.2.5 a 5.2.8 | Saneamiento de HTML, plantillas, correo, SVG | Cumple | No se acepta HTML; los correos escapan el texto (`html.escape`, `app/notificaciones/plantilla.py`); sin plantillas de servidor ni SVG subidos |
| 5.2.4 | Sin `eval` ni ejecución dinámica | Cumple | Bandit en el CI (`.github/workflows/ci-security.yml`) |
| 5.2.6 | Sin SSRF | No aplica | La API no descarga direcciones que dé el usuario; Mailjet solo acepta `https://` (#340) |
| 5.3.1 a 5.3.3 | Codificación de salida según el contexto | Cumple | La PWA pinta con `textContent` (hay prueba: `tests/test_pwa.py`), React escapa, CSP sin scripts en línea |
| 5.3.4, 5.3.5 | Consultas parametrizadas | Cumple | SQLAlchemy Core con parámetros; regla propia de Semgrep contra SQL con f-string (`.semgrep/patitas.yml`) |
| 5.3.6 | Sin inyección en JSON | Cumple | Respuestas serializadas por FastAPI |
| 5.3.7, 5.3.10 | LDAP, XPath, XML | No aplica | No se usan |
| 5.3.8 | Sin inyección de comandos | Cumple | La API no ejecuta comandos. El nodo de video llama a `ffmpeg` con una lista de argumentos fija, sin intérprete (`servicios/video/patitas_video/adaptadores.py`) |
| 5.3.9 | Sin inclusión de archivos | Cumple | Los archivos se guardan con nombres aleatorios; nunca se usa un nombre que dé el usuario |
| 5.5.1 a 5.5.4 | Deserialización segura | Cumple | Solo JSON; no hay `pickle` ni XML |

## V6 Criptografía, V7 Errores y registros

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 6.2.1 | Los módulos criptográficos fallan de forma segura | Cumple | AES-256-GCM: un dato alterado no se descifra, lanza error (`app/seguridad/cifrado.py`); un token inválido es 401 |
| 7.1.1 | Sin credenciales en los registros | Cumple | La bitácora guarda la plantilla de la ruta y sus parámetros, nunca el cuerpo (`app/api/middlewares.py`); el inicio de sesión bloqueado registra solo la IP |
| 7.1.2 | Sin otros datos sensibles en los registros | Parcial | Con Mailjet configurado (producción) cumple. **Sin** proveedor de correo, `NotificadorRegistro` escribe en el log el correo del destinatario y el mensaje (`app/notificaciones/correo.py`). Propuesta P-S6: enmascarar el correo; no se cambió porque una prueba existente fija el comportamiento actual |
| 7.4.1 | Mensaje genérico ante un error inesperado | Cumple | Un error no controlado responde «Internal Server Error», sin traza |

## V8 Protección de datos

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 8.2.1 | Cabeceras contra el caché de datos sensibles | Cumple (desde #361) | `Cache-Control: no-store` en el JSON de la API (`poner_cabeceras`), `tests/test_cabeceras.py` |
| 8.2.2 | Sin datos sensibles en el almacenamiento del navegador | Parcial | El panel no guarda nada. La PWA guarda en el teléfono el reporte **pendiente de envío** (con el contacto, si la persona lo escribió) hasta que se envía; es su propio dato en su propio teléfono y se borra al enviarse (`app/pwa/reportar.js`) |
| 8.2.3 | Se borran al terminar la sesión | Cumple | El token vive en memoria; el service worker no guarda respuestas de la API (`tests/test_pwa.py`) |
| 8.3.1 | Datos sensibles en el cuerpo o en cabeceras, no en la URL | Cumple | Contraseñas y contacto van en el cuerpo |
| 8.3.2 | El usuario puede exportar o borrar sus datos | **No cumple** | Un adoptante no puede borrar su cuenta ni su perfil por sí mismo. Propuesta P-S7 |
| 8.3.3 | Política clara y consentimiento expreso | Cumple | `autoriza_datos` y `autoriza_contacto` obligatorios (Ley 1581); sin autorización no se guarda |
| 8.3.4 | Datos sensibles identificados y con política | Cumple | Contacto y perfil cifrados; RN-14 limita lo que ve el ciudadano; el video original se borra (RNF-08) |

## V9 Comunicaciones, V10 Código malicioso, V11 Lógica de negocio

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 9.1.1 | TLS en toda conexión del cliente | Cumple | Render sirve solo HTTPS; HSTS por un año (`tests/test_cabeceras.py`) |
| 9.1.2, 9.1.3 | Solo TLS 1.2 o superior | Cumple | Comprobado contra producción el 17-nov-2026: TLS 1.0 y 1.1 rechazados; 1.2 y 1.3 responden |
| 10.3.1 | Actualizaciones por canal seguro | No aplica | No hay cliente que se actualice solo; el nodo de video trae `main` por HTTPS desde GitHub |
| 10.3.2 | Integridad del código de terceros | Cumple | Sin CDN ni scripts externos: todo se sirve desde el propio servidor (CSP `script-src 'self'`) |
| 10.3.3 | Sin riesgo de apropiación de subdominios | Cumple | Un solo dominio de Render, sin registros DNS propios |
| 11.1.1 | Los pasos se siguen en orden | Cumple | Estados del reporte y del rescate validados en los servicios y con CHECK en la base |
| 11.1.2, 11.1.4 | Tiempos humanos y freno a la automatización | Cumple | 20 reportes y 5 registros por IP cada 15 min; 5 intentos de sesión (`app/config.py`) |
| 11.1.3, 11.1.5 | Límites de negocio | Cumple | Cupo con `UPDATE` condicional (RN-04), un rescate por rescatista (RN-08), 5 videos en espera |

## V12 Archivos

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 12.1.1 | No se aceptan archivos enormes | Cumple | Video ≤ 50 MB, vista ≤ 5 MB, foto ≤ 300 KB; se cortan mientras llegan (`app/video/almacen.py`) |
| 12.3.1 a 12.3.5 | El nombre del archivo no se usa en rutas ni comandos | Cumple | Nombres aleatorios (`secrets.token_hex`); el nombre original se ignora |
| 12.4.1 | Se guardan fuera de la raíz web | Cumple | En PostgreSQL por trozos; se sirven solo por rutas con sesión |
| 12.4.2 | Se revisan con antivirus | **No cumple** | Solo se comprueba la firma del formato (MP4, MOV, WebM; JPEG, PNG, WebP). Riesgo aceptado: el video lo abre únicamente el nodo de análisis y se borra |
| 12.5.1 | Solo se sirven tipos esperados | Cumple | Foto con su tipo verificado, vista como `video/mp4` |
| 12.5.2 | Lo subido no se interpreta como HTML o script | Cumple | `X-Content-Type-Options: nosniff` en todas las respuestas |
| 12.6.1 | Lista de destinos permitidos (SSRF) | Cumple | El servidor no hace peticiones a direcciones del usuario |

## V13 API y V14 Configuración

| Control | Qué pide | Estado | Evidencia o propuesta |
|---|---|---|---|
| 13.1.1 | Un solo formato y codificación | Cumple | JSON en UTF-8 |
| 13.1.3 | Las URL no exponen datos sensibles | Cumple | Ni tokens ni contraseñas en la URL; el código de seguimiento no revela datos (RN-14) |
| 13.2.1 | Métodos HTTP apropiados | Cumple | Cada ruta declara su método; los demás responden 405 |
| 13.2.2 | Validación de esquema JSON | Cumple | Pydantic en cada entrada |
| 13.2.3 | Protección CSRF en servicios REST | Cumple | Sin cookies (ver 4.2.2) |
| 13.3.1 | Validación de SOAP | No aplica | No hay SOAP |
| 14.2.1 | Componentes al día | Cumple | `pip-audit` y `npm audit` en cada PR y los lunes (#351). Hoy: 0 vulnerabilidades en producción. Quedan 5 en herramientas de **desarrollo** del panel (no llegan al navegador) |
| 14.2.2 | Sin funciones ni ejemplos innecesarios | Cumple | Los datos de demostración están apagados salvo que se activen; `/docs` es la documentación de la API, sin datos |
| 14.2.3 | Recursos externos con integridad (SRI) | Cumple | No hay recursos externos |
| 14.3.2 | Sin modo depuración en producción | Cumple | Uvicorn sin `--reload` ni depuración (`Dockerfile`) |
| 14.3.3 | Las cabeceras no revelan versiones | Cumple | `Server: cloudflare` y `x-render-origin-server: uvicorn`, sin números de versión |
| 14.4.1 | Tipo de contenido con su codificación | Cumple | FastAPI lo pone en cada respuesta |
| 14.4.3 | Política de seguridad de contenido | Cumple | CSP estricta en la PWA, el panel y el inicio (`POLITICA_PWA`), `tests/test_pwa.py` |
| 14.4.4 | `X-Content-Type-Options: nosniff` | Cumple | En todas las respuestas |
| 14.4.5 | HSTS | Cumple | `max-age=31536000` |
| 14.4.6 | `Referrer-Policy` | Cumple (desde #361) | `no-referrer` en todas las respuestas |
| 14.4.7 | No se puede enmarcar desde otro sitio | Cumple (desde #361) | `X-Frame-Options: DENY` en todas; además `frame-ancestors 'none'` en la interfaz |
| 14.5.1 | Solo los métodos HTTP que se usan | Cumple | Ver 13.2.1 |
| 14.5.2 | La cabecera `Origin` no se usa para autenticar | Cumple | Nunca se lee |
| 14.5.3 | CORS con lista de orígenes | Cumple | No hay CORS: solo el mismo origen. Regla de Semgrep contra el comodín con credenciales |

## Lo que queda abierto (decide Brayan)

| ID | Propuesta | Control | Esfuerzo |
|---|---|---|---|
| P-S1 | Rechazar contraseñas de una lista local de las más comunes | 2.1.7 | Bajo. **Ojo:** si la contraseña de demostración o la del administrador en Render fuera una de ellas, habría que cambiarla primero |
| P-S2 | Botón «mostrar contraseña» y medidor de fortaleza en el panel | 2.1.8, 2.1.12 | Bajo |
| P-S3 | Correo al usuario cuando cambia su contraseña (por el outbox) | 2.2.3, 2.5.5 | Bajo |
| P-S4 | Obligar a cambiar la contraseña inicial en el primer ingreso | 2.3.1 | Medio (columna nueva y pantalla) |
| P-S5 | Segundo factor (TOTP) para el administrador | 4.3.1 | Medio |
| P-S6 | Enmascarar el correo en el log del notificador de respaldo | 7.1.2 | Bajo; cambia una prueba existente |
| P-S7 | Que el adoptante pueda borrar su cuenta y su perfil | 8.3.2 | Medio |
| — | Formulario de «cambiar contraseña» en el panel (hoy solo por la API) | 2.1.5 | Bajo |
| — | A-04: IP real detrás del proxy de Render (P-17, ya listo para activar) | 2.2.1, 11.1.4 | Lo activa Brayan en Render |

Ninguna de estas es un fallo que permita entrar sin credenciales o leer datos ajenos; son
controles de nivel 1 que faltan y que se dejan a la vista.
