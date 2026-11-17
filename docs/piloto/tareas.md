# Las 4 tareas del piloto

Quien dirige la sesión **lee cada tarea tal cual** y no explica cómo se hace. El tiempo se mide
desde que termina de leer hasta el **criterio de éxito**. Si la persona se queda atascada
**3 minutos**, se detiene la tarea, se anota «no completó» y se sigue con la siguiente.

Todos los casos son **inventados**. Nadie escribe datos reales.

| | T1 Reportar | T2 Consultar | T3 Confirmar | T4 Aceptar |
|---|---|---|---|---|
| Quién | Cualquier persona | Cualquier persona | Personal veterinario | Rescatista |
| Dónde | PWA `/app/` (Modo piloto) | PWA `/app/` | Panel `/panel/` | Panel `/panel/` |
| Dispositivo | Celular | Celular | Computador o celular | Celular |
| Meta del ERS | **≤ 90 s** (RNF-06) | no tiene | no tiene | no tiene |

## T1 — Reportar una emergencia (ciudadano)

**Preparación:** panel → administrador → **Modo piloto** → «Nuevo participante». Entregar el
celular con la pantalla «Reportar emergencia» abierta.

**Se lee:** «Vas por la calle y ves un perro atropellado frente al parque Santander. No se
levanta y sangra mucho. Usa esta aplicación para reportarlo.»

**Éxito:** aparece el **código de seguimiento** en pantalla.
**El tiempo** lo mide el sistema (del primer toque al código). Meta: 90 segundos o menos.
**Observar:** ¿escribe 20 caracteres sin que se lo pidan dos veces?, ¿usa el GPS o escribe la
dirección?, ¿entiende qué es la comuna?, ¿intenta adjuntar video?

## T2 — Consultar el estado con el código (ciudadano)

**Preparación:** una tarjeta con el código de un **reporte de práctica** creado antes de la
sesión (ver `README.md`). La aplicación abierta en «Reportar».

**Se lee:** «Ayer reportaste un animal y te dieron este código [se entrega la tarjeta]. Averigua
en qué va tu reporte.»

**Éxito:** la persona **dice en voz alta en qué paso va** el reporte (por ejemplo, «lo están
revisando»), leyéndolo de la pantalla.
**Observar:** ¿encuentra «Consultar»?, ¿escribe el código con o sin espacio?, ¿entiende los
pasos y sus fechas?, ¿busca algo que la pantalla no muestra (RN-14: no debe ver la prioridad
ni la descripción)?

## T3 — El veterinario confirma la prioridad (personal veterinario)

**Preparación:** sesión iniciada con la cuenta de demostración de veterinaria. En la cola está
el reporte de práctica de T2 (u otro creado para esta tarea), sin confirmar.

**Se lee:** «Llegó este reporte al refugio [se muestra el código]. Revísalo y decide su
prioridad como lo harías en un día normal.»

**Éxito:** el reporte queda **confirmado** (con la prioridad sugerida, o ajustada con su
justificación) o **descartado** con su motivo, y sale de la cola.
**Observar:** ¿entiende por qué el sistema sugiere esa prioridad (evidencias)?, ¿confía o
ajusta?, si ajusta ¿entiende que debe justificar (RN-16)?, ¿mira el análisis de video si lo
hay?, ¿qué le hizo falta para decidir?

## T4 — El rescatista acepta el rescate (rescatista)

**Preparación:** el reporte de T3 confirmado como **crítico o alto** (si no lo quedó, se
confirma otro de práctica). Sesión iniciada con la cuenta de demostración de rescatista, en
un celular.

**Se lee:** «Estás disponible para rescates. Mira si hay algún caso para ti y hazte cargo.»

**Éxito:** el rescate queda **aceptado** a su nombre (estado «en camino»).
**Opcional, si hay tiempo:** «Ya llegaste y el animal va para el refugio»: marca la llegada y
el resultado.
**Observar:** ¿encuentra la oferta?, ¿le alcanza la información para decidir (ubicación,
qué le pasa al animal)?, ¿entiende que solo puede llevar un rescate a la vez (RN-08)?

## Después de las tareas

1. Cuestionario SUS (`sus.md`), sin comentar nada antes.
2. Las dos preguntas abiertas de la hoja de observación.
3. Agradecer. Al final del día: descartar los reportes de práctica.
