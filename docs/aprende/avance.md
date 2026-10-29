# Avance del plan

## Fase 0 · Preparación

- Integrado el incremento 3 (bundle, #63, #64): avisos con reintento, panel React del
  veterinario, Docker y `render.yaml` en `main`.
- Guía de estudio iniciada: `00-mapa.md`.
- **Render**: el Blueprint aún no está creado. Crearlo lo hace Brayan (es crear cuenta y
  aceptar términos): en Render, *New → Blueprint →* este repositorio. Después, cada merge a
  `main` se despliega solo. **Hecho por Brayan: https://patitas-en-casa-pnnk.onrender.com**

## Fase 1 · Pantallas por rol (#67)

- PR apilados, en orden: #66 (docs) → #68 (administrador inicial) → #69 (cuentas) → #70
  (refugios) → #71 (panel rescatista) → #72 (panel refugio) → #73 (panel administrador) →
  guía de la fase.
- Probado en el navegador contra una API en memoria con cuentas de demostración.
- Para Render: agregar `PATITAS_ADMIN_CORREO` y `PATITAS_ADMIN_CONTRASENA` en *Environment*.
- Falta: que ingresos y ocupación usen el refugio del coordinador (fase 2).
- Guía: `fase-1-pantallas-por-rol.md`.

## Fase 2 · Refugio completo (#75)

- PR apilados, en orden: #76 (D-06, D-07) → #77 (versión del modelo) → #78 (descartar) →
  #79 (duplicados) → #80 (cupos por refugio) → #81 (ficha clínica) → #82 (egresos + panel de
  la cola) → #83 (panel de fichas) → guía de la fase.
- Probado en el navegador: descartar un duplicado y agregar una nota a la ficha.
- Falta: alerta de cupo por correo a los coordinadores **del refugio** (hoy va a la lista
  `PATITAS_CORREOS_COORDINADORES`); exportar la ficha queda para la fase 5.
- Guía: `fase-2-refugio-completo.md`.

## Fase 3 · Adopción (#85)

- PR apilados, en orden: #86 (adoptante y perfil) → #87 (publicar) → #88 (solicitar) → #89
  (decidir, RN-05, RN-11, seguimientos) → #90 (registrar seguimientos) → #91 (PDF) → #92
  (panel del adoptante) → #93 (panel del coordinador) → guía de la fase.
- Probado en el navegador de punta a punta: publicar → perfil → solicitar → aprobar →
  seguimientos programados. El PDF se abrió y se ve bien.
- Falta: devolución de un animal adoptado (RN-13: hoy el compromiso la pide, pero el sistema
  no la registra); límite de registros por IP en `POST /adoptantes` (anotado en
  `DEUDA_TECNICA.md` como DT-09).
- Guía: `fase-3-adopcion.md`.

## Fase 4 · IA (#95)

- PR apilados, en orden: #96 (clasificador entrenado) → #97 (compatibilidad) → #98
  (jornada, húngaro) → #99 (video: puerto y RN-07) → #100 (panel) → guía de la fase.
- El modelo de triaje se entrenó con datos sintéticos: sus métricas no son clínicas.
- No construido: análisis de video con MediaPipe (DT-10, con plan en `DEUDA_TECNICA.md`).
- Guía: `fase-4-ia.md`.

## Fase 5 · Cierre (#102)

- PR apilados, en orden: #103 (bitácora) → #104 (indicadores) → #105 (exportar) → #106
  (panel) → versión 1.0.0 y esta guía.
- 568 pruebas en verde, cobertura 98 %; vitest 21; build del panel sin errores.
- Guía: `fase-5-cierre.md`.

## Resumen para Brayan

**Qué quedó:** todo el plan, en PR pequeños y apilados (#66 a #107), cada uno con su CI en
verde. Ninguno está integrado a `main`: la regla 2 de `CLAUDE.md` pide tu revisión (P-01).

**Cómo integrarlos:** en orden, del más bajo al más alto. Cada PR apunta a la rama del
anterior; al integrar uno con *squash*, GitHub cambia la base del siguiente a `main`. Si un
PR muestra conflictos, pídeme «rebasa la cadena sobre main». Al terminar, crea la etiqueta
`v1.0.0` sobre `main`.

**Render:** crear el Blueprint (*New → Blueprint →* este repositorio) es tuyo (cuenta y
términos). Luego agrega en *Environment* `PATITAS_ADMIN_CORREO` y
`PATITAS_ADMIN_CONTRASENA`. Cada merge a `main` se despliega solo. **URL: https://patitas-en-casa-pnnk.onrender.com**

**Qué falta o quedó como deuda:**
- DT-04 (en parte): validar el modelo de triaje con reportes reales.
- DT-09: limitar por IP el registro público de adoptantes.
- DT-10: análisis de video con MediaPipe (no cabe en Render gratis; plan escrito).
- DT-07 y DT-08 (del incremento 3) siguen abiertas.
- RN-13 (devolución de un animal adoptado) solo está en el texto del compromiso.
- Revisa `preguntas-para-brayan.md`: P-01 a P-06.

## Integración y despliegue (29 de octubre de 2026)

- Por indicación de Brayan, la cadena de PR apilados se integró en **un solo PR (#108)**: se
  hizo merge de `main` en `trabajo/cierre`, los 5 conflictos se resolvieron con la versión
  de `trabajo/cierre` (el merge no cambió ningún archivo), 573 pruebas en verde con
  PostgreSQL y CI en verde. Los PR #69 a #107 se cerraron con «Integrado en el PR de
  trabajo/cierre».
- Render desplegó solo: la API responde versión 1.0.0, la PWA, el panel y el catálogo de
  adopción responden 200 (las migraciones `0010` a `0021` corrieron) y `/cola` sin sesión
  responde 401. URL: https://patitas-en-casa-pnnk.onrender.com

## Cómo crear las variables en Render (paso a paso)

Las contraseñas **no están en el código**: tú las escribes en Render y el sistema las lee al
arrancar. Hazlo así:

1. Entra a https://dashboard.render.com e inicia sesión.
2. En la lista, haz clic en el servicio web **patitas-en-casa** (no en la base de datos).
3. En el menú de la izquierda, haz clic en **Environment**.
4. Pulsa **Add Environment Variable** (o **Edit** si ya existe) y crea, una por una:

   | Nombre (Key) | Valor (Value) | Para qué sirve |
   |--------------|---------------|----------------|
   | `PATITAS_ADMIN_CORREO` | tu correo real, p. ej. `brayan@…` | Tu cuenta de administrador. |
   | `PATITAS_ADMIN_CONTRASENA` | una contraseña tuya de 12 caracteres o más | Contraseña de esa cuenta. |
   | `PATITAS_DEMO_ACTIVA` | `true` | Carga los datos de demostración una sola vez. |
   | `PATITAS_DEMO_CONTRASENA` | otra contraseña de 12 caracteres o más | La usan **todas** las cuentas de demostración. |

5. Pulsa **Save Changes**. Render reinicia el servicio solo (tarda unos minutos).
6. Abre https://patitas-en-casa-pnnk.onrender.com/panel/ y entra con cualquiera de estas cuentas y la contraseña que pusiste en
   `PATITAS_DEMO_CONTRASENA`:

   | Rol | Correo |
   |-----|--------|
   | Administrador | `admin@demo.patitas.co` |
   | Veterinaria | `veterinaria@demo.patitas.co` |
   | Coordinador | `coordinador@demo.patitas.co` |
   | Rescatista | `rescatista@demo.patitas.co` |
   | Adoptante | `adoptante@demo.patitas.co` |
   | Alcaldía | `alcaldia@demo.patitas.co` |

Qué hay que saber:

- Las cuentas de demostración son ficticias (el dominio `demo.patitas.co` no existe).
- Los datos se cargan **una sola vez**: si la cuenta `veterinaria@demo.patitas.co` ya existe,
  no se vuelve a cargar nada aunque Render reinicie. Para empezar de cero hay que borrar la
  base (o crear una nueva) en Render.
- Para no volver a cargarlos en una base nueva, cambia `PATITAS_DEMO_ACTIVA` a `false`.
- No uses la misma contraseña para tu cuenta de administrador y para la demostración: la de
  demostración la verá quien asista a la presentación.
- Si alguna variable falta o la contraseña es corta, la API arranca igual y en *Logs* aparece
  el motivo (nunca la contraseña).

## Brechas del ERS cerradas después del #108

Al leer el ERS final (v5.0) aparecieron requisitos que estaban incompletos. Se cerraron, cada
uno con su PR, CI en verde y comprobación en Render: datos de demostración (#110), contacto
cifrado del ciudadano RF-18/RNF-08 (#112), visita previa y devoluciones RF-27/RF-10 (#114),
fotos RF-25 (#116), indicadores y exportación completos RF-30/RF-31/RNF-16 (#118), prueba de
carga, sondeo y OWASP ZAP RNF-01/04/05/14 (#120) y los arreglos de la prueba de punta a punta
(#122). En el #108 ya habían entrado el rol Alcaldía (RF-13), la dirección del refugio
(RF-14), el historial de acceso (RF-16), la alerta por refugio (RF-07), el refugio en el
compromiso (RF-29), la discrepancia texto/video (RF-19) y la complejidad ≤ 10 (RNF-10).
Detalle completo en `trazabilidad.md`.

## Prueba de punta a punta (29 de octubre de 2026)

**Dónde.** Las normas de seguridad del asistente no le permiten escribir contraseñas en un
sitio de producción. Por eso:

- **En Render (https://patitas-en-casa-pnnk.onrender.com):** todo lo público, en celular (375 × 812) y escritorio: la PWA
  (reportar solo con teclado, código de seguimiento y consulta del estado), la pantalla de
  inicio del panel, el catálogo público, cabeceras, TLS y OWASP ZAP. Se creó **un reporte de
  prueba**, marcado «PRUEBA de punta a punta… (no es real)», con código `CMTNWEMQ`:
  **descártalo** desde la cola como veterinaria («falso»).
- **En local, con el mismo código de `main` y los datos de demostración:** el recorrido de
  cada rol con sesión (veterinaria, rescatista, coordinador, adoptante, administrador y
  Alcaldía), en celular y escritorio, solo con teclado.

**Resultados.**

| Qué | Resultado |
|-----|-----------|
| Errores en la consola | Ninguno, en ninguna pantalla (Render y local). |
| Desborde horizontal a 375 px | Ninguno. |
| Solo con teclado | Inicio de sesión, «Saltar a la cola», confirmar, aceptar rescate, pedir adopción y reportar en la PWA: todo funciona. |
| Campos sin etiqueta / imágenes sin `alt` | Ninguno. |
| Peso de la PWA en Render (RNF-07) | 28 KB (límite 1,5 MB); panel 61 KB. |
| TLS (RNF-05) | 1.0 y 1.1 rechazados; 1.2 aceptado. |
| OWASP ZAP (RNF-05) | 0 hallazgos altos; de 5 advertencias bajas quedan 3 informativas. |
| Carga en local (RNF-01, RNF-14) | p95 2,84 s con 30 reportes a la vez y 50 usuarios del panel; 0 errores. |

**Fallas encontradas y corregidas (#122):**

1. En el celular, tras elegir un reporte, el foco se quedaba en la lista y había que recorrer
   todos los reportes con Tab para llegar a «Confirmar». Ahora el foco va al detalle.
2. Los botones con el nombre del animal medían 21 px de alto (WCAG 2.2 pide 24 px).
3. Faltaban las cabeceras HSTS, `Permissions-Policy` y `Cross-Origin-Opener-Policy`.
4. El JS del panel viajaba sin comprimir: ahora va con gzip.

Observación que no es una falla de producción: con el doble en memoria (solo pruebas locales)
la ocupación de «Indicadores» no ve los ingresos nuevos; con PostgreSQL (Render) sí.

**Lo que debes probar tú en Render** (con tu contraseña de demostración): el guion de
`guion-demo.md`. Es el mismo recorrido que se probó en local.

## Fase 6 · Análisis de video con trabajador local (#125, v1.1.0)

Hugging Face ya cobra los Spaces Docker, así que el análisis corre en **tu PC**: un
trabajador le pide los videos a la API de Render, los analiza y devuelve el resultado. Se
integró en 17 PR pequeños (#126 a #142), cada uno con CI en verde y Render revisado después.
Guía completa: `fase-6-video.md`; instalación: `servicios/video/README.md`.

**Qué quedó funcionando:**

- La PWA permite adjuntar un video (≤ 60 s, ≤ 50 MB) y lo sube después del reporte. En
  Render ya está activo: `render.yaml` generó `PATITAS_VIDEO_TOKEN`.
- La API guarda el video unos minutos, lo pone en la cola `analisis_video` y lo borra al
  terminar. Si nadie lo analiza en 6 h, o se pierde, manda el texto (falla segura).
- El trabajador (`servicios/video/`): MediaPipe Object Detector + DeepLabCut
  SuperAnimal-Quadruped + medidas de la marcha + red neuronal pequeña con reglas de seguridad.
- El panel muestra el análisis, la discrepancia con el texto y una tira de 3 cuadros.

**Prueba de humo con modelos reales** (GitHub Actions, CPU): el perro con ataxia (CC0) y el galgo con polineuropatía (CC BY 2.5) salieron **media** con confianza 0,95 («cojea», «paso irregular»); el labradoodle sano salió **no concluyente** (puntos poco seguros: manda el texto). Cada video tardó de 36 a 82 s con 1,3 a 1,5 GB de memoria. Tabla y enlaces en `fase-6-video.md`.

**Hallazgos que debes conocer:**

1. **MediaPipe Pose no sirve para perros** (solo conoce personas): se usa MediaPipe para
   encontrar al animal y DeepLabCut para sus puntos.
2. **En tu Windows, DeepLabCut no arranca directo:** el Control inteligente de aplicaciones
   bloqueó DLL de `torchvision` (y de algunas versiones de `scikit-learn` y `numba`). No lo
   apagues; usa **WSL2** como dice el README.
3. **Licencia de SuperAnimal:** solo académica y no comercial. Sirve para la universidad.
4. **El modelo del video se entrenó con datos sintéticos** y los umbrales se calibraron con 3
   videos públicos: hace falta validarlo con videos etiquetados por veterinarios (DT-04).
   Por eso el video solo puede **subir** la prioridad.

### Lo que debes hacer tú (paso a paso)

1. **Instala WSL2** (PowerShell como administrador): `wsl --install -d Ubuntu-24.04`,
   reinicia y abre «Ubuntu». Crea tu usuario de Linux cuando te lo pida.
2. **Instala el trabajador** en Ubuntu con el script `instalar_nodo.sh` (paso 2 de
   `servicios/video/README.md`; unos 3 GB, la primera vez tarda).
3. **Pruébalo con un video tuyo** (sección «Probar con un video tuyo»). Graba a un perro de
   lado, caminando, 10 a 20 s, que se vea completo.
4. **Copia el token de Render:** Render → servicio `patitas-en-casa` → *Environment* →
   `PATITAS_VIDEO_TOKEN` → ojo para verlo → copiar. No lo pegues en ningún archivo del
   repositorio ni en un chat.
5. **Arranca el trabajador** en Ubuntu: `bash ~/patitas/servicios/video/arrancar_nodo.sh`.
   Pide el token sin mostrarlo (pégalo con clic derecho). Déjalo abierto mientras quieras
   analizar videos (por ejemplo, durante la demostración).
6. **Ensaya el paso 1b de `guion-demo.md`**: reporte con video desde el celular → en la
   terminal aparece «trabajo N analizado» → en el panel, «Análisis de video: listo».
7. **Si quieres apagar el video en producción**, borra `PATITAS_VIDEO_TOKEN` en Render: la PWA
   dirá que el reporte se atiende con la descripción.
8. Para mejorar el modelo: graba (o consigue) videos con la prioridad que les daría un
   veterinario y reentrena con `servicios/video/entrenamiento/entrenar.py --datos`.

Nota: el plan `PLAN_VIDEO_PARA_CLAUDE_CODE.md` que quedó en tu carpeta todavía describe
Hugging Face; se siguió la arquitectura de tu mensaje (trabajador local).

## Tareas de cierre del 29 de octubre de 2026

Seis tareas pedidas por Brayan, cada una en PR pequeños con CI en verde.

### 1. Scripts del nodo de video (#143)

- `servicios/video/instalar_nodo.sh`: instala todo en Ubuntu/WSL2 (programas del sistema,
  código, entorno de Python, librerías de IA) y comprueba que carguen. Se puede repetir para
  actualizar.
- `servicios/video/arrancar_nodo.sh`: pide el token con `read -s` (no se ve), quita el fin
  de línea de Windows si lo pegas desde allá, ofrece guardarlo en `~/.patitas-video/token`
  con permisos solo para tu usuario y nunca lo imprime. `--video archivo` analiza sin token.
- El README empieza con 3 pasos para quien nunca usó Linux. `.gitattributes` obliga a que
  los `.sh` queden con fin de línea de Linux aunque se editen en Windows.
- Pruebas: `tests/test_video_nodo.py` (sintaxis, el token no aparece en la salida, se
  guarda solo si se pide). No se probó en un Ubuntu real: el paso 2 lo vas a correr tú.

### 2. Página de inicio pública (#145)

- `https://patitas-en-casa-pnnk.onrender.com/` ya no salta a la PWA: muestra una página que
  explica el proyecto en 30 segundos (problema, 6 pasos, 7 roles y tecnología) con tres
  botones grandes. «Adoptar» abre directamente el registro de adoptante del panel
  (`/panel/#registro`).
- Es HTML y CSS sin JavaScript (`app/inicio/`), con la misma CSP estricta de la PWA. Se
  revisó en un celular de 375 px: sin desplazamiento horizontal y botones de 56 px de alto.
- Para la sustentación: si te preguntan «¿por qué sin JavaScript?», porque es una página
  que solo informa; así carga rápido con mala señal y no hay nada que atacar.
- Pruebas: `tests/test_inicio.py`.

### 3. Accesibilidad medida (#147)

- `scripts/accesibilidad/revisar.mjs` abre un navegador real y pasa **axe-core** por cada
  pantalla (pública y de cada rol, en claro, oscuro y celular de 320 px) y **Lighthouse** por
  las pantallas públicas. Corre en el CI: si algo empeora, el PR queda en rojo.
- Encontró 2 fallas, las dos en el panel y de estructura (sin región `<main>` en el inicio de
  sesión y sin título de nivel 1 con sesión). Corregidas: **0 fallas y Lighthouse 100**.
  Ninguna de contraste.
- Informe completo, con lo que las herramientas no prueban: `docs/aprende/accesibilidad.md`.
- **Lo que te toca:** escuchar el guion de la demostración con NVDA (gratis) o TalkBack, unos
  20 minutos, y anotar lo que suene confuso.

### 4. Seguridad de los adoptantes (#149)

**Parte 1, DT-09 pagada.** El registro público de adoptantes tenía dos huecos:

- **Sin límite:** un robot podía crear miles de cuentas. Ahora cada IP puede registrar 5
  cuentas cada 15 minutos (se reutilizó el `LimiteIntentos` del inicio de sesión con otra
  clave, `registro:<ip>`); la sexta recibe 429 y cuánto esperar.
- **Revelaba correos:** si el correo ya existía respondía 409, así que cualquiera podía
  averiguar quién tiene cuenta. Ahora la respuesta es idéntica en los dos casos y la cuenta
  existente no cambia. Como el hash Argon2id se calcula antes de descubrir que el correo
  existe, ni siquiera el tiempo de respuesta lo delata.
- Para la sustentación: «¿y si el dueño del correo olvidó que tenía cuenta?» Entra con su
  contraseña de siempre; el mensaje lo dice. Lo ideal sería avisarle por correo, pero en
  producción no hay SMTP (P-12).

**Parte 2, perfiles cifrados (RNF-08).** El perfil del adoptante (vivienda, si hay niños,
horas solo, experiencia…) se guarda cifrado con AES-256-GCM, con la misma clave
`PATITAS_CLAVE_DATOS` del contacto del ciudadano (Render ya la tiene).

- En la tabla queda solo el correo, la fecha y un texto ilegible (`datos_cifrados`); las
  columnas en claro quedan vacías. Una restricción de la base impide un perfil «a medias».
- La migración `0026` no conoce la clave, así que los perfiles viejos se cifran solos la
  primera vez que arranca la API (`cifrar_perfiles_en_claro`); si ya están cifrados, no hace
  nada.
- Las recomendaciones siguen funcionando: el perfil se descifra en memoria al leerlo.
- Para la sustentación: «¿y si pierden la clave?» Los perfiles no se pueden leer; el
  adoptante tendría que llenarlo de nuevo. Por eso la clave vive en Render y conviene
  guardarla también en un gestor de contraseñas (P-13).

## Resumen final para Brayan

**Versión publicada: v1.1.0** (etiqueta `v1.1.0` y *release* en GitHub; añade el análisis
de video de la fase 6 sobre la v1.0.0), desplegada en https://patitas-en-casa-pnnk.onrender.com.

**Qué quedó funcionando** (en `main`, desplegado y probado):

- PWA ciudadana: reportar sin cuenta (también sin señal), contacto opcional cifrado y
  consulta del estado.
- Triaje con reglas + modelo TF-IDF (datos sintéticos), cola, confirmar, ajustar o descartar
  con justificación, duplicados y bitácora de decisiones.
- Rescates: ofertas por comuna, aceptar, llegué, resultado, escalamiento y avisos con
  reintentos (outbox).
- Refugio: varios refugios, ingresos con ficha e historial, egresos, cupos con alerta al 90 %.
- Adopción: perfil, recomendaciones con puntaje y razones, fotos, solicitudes, visita previa,
  aprobación con restricciones duras, seguimientos 30/90/180, devoluciones y compromiso PDF.
- Administración y control: seis roles, cuentas, suspensión, historial de acceso, indicadores,
  exportación anonimizada y bitácora inmutable.
- Calidad: más de 650 pruebas con PostgreSQL real, 97 % de cobertura, complejidad ≤ 10,
  gitleaks, sondeo de disponibilidad y OWASP ZAP.

**Qué no y por qué** (detalle en `trazabilidad.md`):

- Video (RF-03): funciona con el trabajador local, pero su modelo no está validado con
  veterinarios y el trabajador debe estar encendido (fase 6, arriba).
- Disponibilidad del 99 % (RNF-04): el plan gratis se duerme; hay sondeo, no garantía.
- Recall con datos de veterinarios (RNF-03): el modelo se validó con datos sintéticos.
- Usabilidad con personas (RNF-06): necesita participantes reales.
- Respaldo diario (RNF-15): listo para integrar, pero es tu decisión (P-07).
- Lector de pantalla y contraste medidos con herramienta (RNF-11): falta esa revisión.

**Qué debes hacer tú:**

1. En Render → servicio → *Environment* (paso a paso arriba): `PATITAS_ADMIN_CORREO`,
   `PATITAS_ADMIN_CONTRASENA`, `PATITAS_DEMO_ACTIVA=true` y `PATITAS_DEMO_CONTRASENA`.
   Comprueba que exista `PATITAS_CLAVE_DATOS` (la genera `render.yaml`; si no aparece,
   créala con 32 caracteres o más al azar).
2. Descarta el reporte de prueba `CMTNWEMQ`.
3. Ensaya `guion-demo.md` en Render.
4. Responde las preguntas pendientes de `preguntas-para-brayan.md`: P-01 (pegar la regla 2 en
   `CLAUDE.md`), P-07 (respaldo), P-08 (correo real), P-09 (video) y P-10 (prueba con
   usuarios).
5. Estudia en este orden: `00-mapa.md`, las seis guías de fase (cada una con sus 5
   preguntas y respuestas), `preguntas-sustentacion.md` y `trazabilidad.md`.
