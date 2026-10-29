# Fase 6 · Análisis de video del animal

Issue #125. PR en orden: #126 → #127 → #128 → #129 → #130 → #131 → #132 → #133 → #134 →
#135 → #136 → #137 → #138 → #139 → #140 → este (#141). Cada uno con CI en verde y comprobación de Render después del merge.

## Qué hace

| Requisito | Qué se construyó |
|-----------|------------------|
| RF-01 | El ciudadano adjunta un video opcional (≤ 60 s, ≤ 50 MB) desde la PWA, sin cuenta. |
| RF-03 | Un **trabajador local** analiza la marcha del animal: MediaPipe Object Detector + DeepLabCut SuperAnimal-Quadruped + medidas de la marcha + red neuronal pequeña. |
| RF-19, RN-07 | El resultado del video se fusiona con el del texto: gana la prioridad más alta y la discrepancia queda registrada y visible en el panel. |
| RNF-02 | 5 cuadros por segundo para que 60 s de video se analicen en ≤ 3 min (medido en la prueba de humo). |
| RNF-08 | El video nunca se guarda para siempre: se borra al terminar, falle o no. Solo quedan las medidas, las evidencias y una tira pequeña. |
| RNF-09 | Cada resultado del video trae al menos 3 evidencias en lenguaje claro. |

## La corrección técnica más importante

El plan original decía «MediaPipe Pose». **MediaPipe Pose solo detecta el cuerpo de una
persona (33 puntos humanos); con un perro o un gato no sirve.** El diseño correcto conserva
MediaPipe pero para otra tarea:

1. **MediaPipe Object Detector** (EfficientDet-Lite0, clases COCO «dog» y «cat»): dice si en
   el cuadro hay un perro o un gato y dónde está (un recuadro).
2. **DeepLabCut SuperAnimal-Quadruped** (EPFL, HRNet-w32): dentro de ese recuadro da 39
   puntos del cuerpo de un cuadrúpedo (patas, rodillas, lomo, cuello, cola). Ya viene
   entrenado: no se entrena nada.
3. **Medidas de la marcha** (`marcha.py`): con esos puntos se calcula si está de pie, si apoya
   las cuatro patas, si una pata se mueve distinto de su par (cojera), si el paso es regular y
   cuánto se desplaza.
4. **Clasificador** (`clasificador.py`): una red neuronal pequeña (MLP 5-8-4) convierte esas
   medidas en prioridad y confianza. Encima del modelo hay **reglas de seguridad**: «no se pone
   de pie» o «no apoya una pata» nunca queda por debajo de *alta*.

## Por qué se hizo así

1. **Trabajador local en vez de un servicio en la nube.** El análisis necesita unos 3 GB de
   librerías y no cabe en los 512 MB de Render gratis; Hugging Face ya cobra los Spaces
   Docker. Así que corre en una PC del equipo.
2. **El trabajador pide, no recibe.** Llama a Render cada 15 s («¿hay trabajo?»). No hay que
   abrir puertos del router de la casa ni exponer la PC a internet.
3. **Cola en PostgreSQL, como el outbox de avisos.** Cada video es una fila de
   `analisis_video` con estados `pendiente → enviado → terminado / no_concluyente / fallido`.
   El reclamo usa `FOR UPDATE SKIP LOCKED`: dos trabajadores nunca reciben el mismo video.
4. **El video vive poco.** Se escribe por partes en el disco temporal de Render (nunca entero
   en memoria) y se borra apenas el trabajador entrega el resultado. Si Render se reinicia y
   el archivo se pierde, el trabajo queda «fallido» y **manda el texto** (falla segura).
5. **Solo quien creó el reporte sube su video.** El ciudadano no tiene cuenta; la prueba de
   que es él es la clave de idempotencia (`Idempotency-Key`) que su teléfono generó al
   crear el reporte. Además: dentro de 30 minutos y una sola vez.
6. **El veterinario manda.** Si el veterinario ya confirmó o descartó el reporte cuando llega
   el resultado del video, no se toca (`actualizar_triaje` es un `UPDATE` condicional,
   RN-16).
7. **Datos sintéticos, dichos como tales.** No hay videos de perros etiquetados por
   veterinarios. La red se entrenó con medidas generadas al azar y etiquetadas con criterios
   clínicos sencillos. Mide que aprendió esos criterios, no que acierte con animales reales
   (DT-04). El script acepta un CSV etiquetado para reentrenar cuando existan.
8. **Las piezas pesadas entran por puertos.** `analisis.py` define `LectorCuadros`,
   `DetectorAnimal`, `EstimadorPuntos` y `DibujanteTira`. En las pruebas se usan dobles; el
   CI de la API no instala 3 GB.

## Recorrido de una petición: un video de un perro cojo

1. El ciudadano llena el reporte en la PWA y elige un video de 12 s. `reportar.js` lee su
   duración con un `<video>` sobre un `blob:` local y muestra «Video listo: 12 s · 8.4 MB».
2. Pulsa **Enviar**: `POST /reportes` con la `Idempotency-Key` del teléfono. Llega el código.
3. La PWA hace `POST /reportes/{codigo}/video` con la misma clave y el archivo.
   `ServicioVideo.autorizar_subida` comprueba la clave, los 30 min y que no haya otro video.
   `AlmacenEnDisco.guardar` escribe por partes, corta a los 50 MB y revisa la firma MP4/WebM.
   Se crea la fila `pendiente`. La PWA muestra «Video recibido, se está analizando».
4. El trabajador (`trabajador.py`) hace `POST /video/trabajos/reclamar` con `X-Video-Token`;
   la fila pasa a `enviado`. Descarga el video con `GET /video/trabajos/{id}/archivo`.
5. `analisis.py`: OpenCV saca 5 cuadros por segundo → MediaPipe encuentra al perro →
   DeepLabCut da sus 39 puntos → `marcha.medir` da «asimetría 0,64; apoya las 4 patas» →
   el MLP dice *media* y el resultado lleva «cojea: una pata se mueve 64 % distinto de su par».
6. El trabajador hace `POST /video/trabajos/{id}/resultado` y borra su copia local.
7. `ServicioVideo.terminar` llama `aplicar_video`: si el video es más grave que el texto, sube
   la prioridad (RN-07), agrega las evidencias «video: …» y marca la discrepancia (RF-19).
   Borra el video del disco de Render.
8. La veterinaria abre el reporte en la cola: ve «Análisis de video: listo», las evidencias,
   la discrepancia y la tira de 3 cuadros con los puntos dibujados.

## Archivos a leer, en orden

1. `servicios/video/patitas_video/marcha.py` (medidas y umbrales).
2. `servicios/video/patitas_video/clasificador.py` y `servicios/video/entrenamiento/entrenar.py`.
3. `app/video/modelos.py` (estados), `app/video/repositorio.py`, `app/video/repositorio_postgres.py`.
4. `app/video/servicio.py` (casos de uso y falla segura) y `app/triaje/video.py` (RN-07).
5. `app/video/almacen.py` y `app/api/video.py` (rutas).
6. `servicios/video/patitas_video/cliente.py`, `trabajador.py`, `analisis.py`, `adaptadores.py`.
7. `app/pwa/reportar.js` (busca «Video opcional») y `panel/src/VideoDelReporte.tsx`.
8. `servicios/video/README.md` (cómo instalarlo y por qué WSL2).

## Cómo probarlo

- Pruebas: `pytest tests/test_video_marcha.py tests/test_video_clasificador.py
  tests/test_video_contrato.py tests/test_video_trabajos.py tests/test_video_api.py
  tests/test_video_trabajador.py tests/test_video_analisis.py`.
- Con modelos reales: GitHub → Actions → «Video: prueba de humo» → Run workflow, con enlaces
  de videos de licencia libre (resultados abajo).
- De punta a punta: sigue `servicios/video/README.md` y el paso 1b de `guion-demo.md`.

## Prueba de humo con modelos reales

Flujo «Video: prueba de humo» (GitHub Actions, CPU de 4 núcleos, sin GPU), con tres videos
de Wikimedia Commons. El tiempo incluye cargar los modelos (unos 20 s).

| Video (licencia) | Perro visible | Resultado | Tiempo · memoria |
|---|---|---|---|
| [Perro con ataxia hereditaria](https://commons.wikimedia.org/wiki/File:Canine-Hereditary-Ataxia-in-Old-English-Sheepdogs-and-Gordon-Setters-Is-Associated-with-a-Defect-in-pgen.1003991.s010.ogv) (CC0, Agler et al., PLOS Genetics) | 68 de 68 cuadros | **media**, 0,95: «cojea: una pata se mueve 65 % distinto de su par», «el paso es irregular» | 57 s · 1,4 GB |
| [Galgo con polineuropatía](https://commons.wikimedia.org/wiki/File:A-Deletion-in-the-N-Myc-Downstream-Regulated-Gene-1-(NDRG1)-Gene-in-Greyhounds-with-Polyneuropathy-pone.0011258.s004.ogv) (CC BY 2.5, Drögemüller et al., PLOS ONE) | 98 de 175 | **media**, 0,95: «el paso es irregular» | 36 s · 1,3 GB |
| [Labradoodle en Berlín](https://commons.wikimedia.org/wiki/File:2015-11-11_Labradoodle_Berlin.webm) (CC BY-SA 4.0) | 56 de 62 | **no concluyente**: los puntos del cuerpo salen con confianza 0,2–0,3 (manda el texto) | 82 s · 1,5 GB |

**Cómo se llegó aquí (con datos, no a ojo).** La primera corrida dio «no concluyente» en los
tres. El diagnóstico (`python -m patitas_video.diagnostico video`) mostró que el detector
encuentra al perro (mediana 0,60–0,82), pero los puntos de SuperAnimal rondan 0,3–0,6 y el
medio del lomo es el más dudoso (0,08–0,36). Se bajó el umbral de 0,5 a 0,3, el lomo se toma
entre cuello y cola cuando falta (#139), y se corrigió un doble conteo de los cuadros sin
perro (#140).

**Lo que esto NO demuestra.** Los dos perros con enfermedad de la marcha salieron *media*,
lo que tiene sentido, pero son 3 videos: no es una validación. Falta un perro sano que dé
*baja* con un video claro (el labradoodle no sirvió) y, sobre todo, videos etiquetados por
veterinarios (DT-04). RNF-02 sí se cumple: menos de 1,5 min por video en una CPU modesta.

## Lo que no está validado (dicho claro)

- **Los umbrales y la red no se validaron con veterinarios.** Son valores razonados y datos
  sintéticos (DT-04). Antes de confiar en el video para bajar una prioridad haría falta un
  conjunto de videos etiquetados; por eso el video solo puede **subir** la prioridad (RN-07).
- **En Windows directo no corre** en la PC de desarrollo: el Control inteligente de
  aplicaciones bloqueó DLL de `torchvision` (y de algunas versiones de `scikit-learn` y
  `numba`). Por eso la guía usa WSL2.
- **Licencia de SuperAnimal-Quadruped:** solo uso académico, no comercial y no transferible.
  Sirve para este proyecto universitario; para un uso real del refugio habría que pedir
  licencia a la EPFL o cambiar de modelo.

## Preguntas de práctica

1. ¿Por qué no se usó MediaPipe Pose para la marcha del perro?
2. Si el trabajador local está apagado toda la noche, ¿qué le pasa a un video que llega a las
   10 p. m.? ¿Y al reporte?
3. El ciudadano no tiene cuenta. ¿Cómo sabe la API que quien sube el video es el mismo que
   creó el reporte?
4. ¿Qué pasa si el veterinario confirma el reporte como *media* justo un segundo antes de que
   el video diga *alta*?
5. ¿Por qué la red neuronal del video tiene reglas de seguridad encima, y por qué el video
   solo puede subir la prioridad?

### Respuestas

<details><summary>Respuesta 1</summary>

Porque MediaPipe Pose solo conoce el cuerpo humano (33 puntos de una persona). Con un perro
da puntos sin sentido o nada. Se usa MediaPipe Object Detector para encontrar al perro o gato
y DeepLabCut SuperAnimal-Quadruped, que sí está entrenado con cuadrúpedos, para los puntos.

</details>

<details><summary>Respuesta 2</summary>

El video queda `pendiente` en el disco temporal de Render. Si Render se duerme o se reinicia,
el archivo se pierde y el trabajo pasa a `fallido`; si no, a las 6 horas `revisar()` lo da por
vencido y lo borra. En cualquier caso el reporte sigue con la prioridad del texto y en la cola
del veterinario: el video ayuda, pero nunca detiene la atención (falla segura).

</details>

<details><summary>Respuesta 3</summary>

Con la clave de idempotencia. El teléfono generó una clave aleatoria de 32 caracteres al crear
el reporte y la API la guardó junto al código. Para subir el video hay que enviar esa misma
clave; quien solo conoce el código (por ejemplo, alguien que lo vio) no la tiene. Además hay
un límite de 30 minutos y un solo video por reporte.

</details>

<details><summary>Respuesta 4</summary>

Nada cambia. `actualizar_triaje` es un `UPDATE ... WHERE estado NOT IN ('confirmado',
'descartado')`: como el reporte ya está confirmado, la fila no cumple la condición y no se
toca. El análisis queda guardado con su discrepancia para que se vea, pero la decisión de la
persona manda (RN-16).

</details>

<details><summary>Respuesta 5</summary>

Porque se entrenó con datos sintéticos y podría equivocarse con un animal real. Las reglas
garantizan que los dos signos más claros de gravedad (no se pone de pie, no apoya una pata)
nunca queden por debajo de *alta*. Y como el modelo no está validado, solo puede subir la
prioridad: un error suyo cuesta, a lo sumo, una revisión de más, nunca que un caso grave espere.

</details>
