# Fase 4 · Inteligencia artificial

Issue #95. PR apilados: #96 → #97 → #98 → #99 → #100 → este. Se revisaron por separado y se integraron a `main` juntos en el **#108**.

## Qué hace

| Requisito | Qué se construyó |
|-----------|------------------|
| RF-02, RNF-03, RNF-09 | Clasificador TF-IDF + regresión logística entrenado con datos **sintéticos**; se combina con las reglas y solo puede subir la prioridad; ≥ 3 evidencias. |
| RF-20 | La versión guardada pasa a `reglas-v0+tfidf-lr-v1`. |
| RF-09, RNF-16 | Compatibilidad adoptante–animal: puntaje 0–100, 3 razones, alertas, sin atributos protegidos. |
| RF-28 | Propuesta de asignación global en jornadas con el algoritmo húngaro. |
| RF-19, RN-07 | Fusión texto + video («gana la más alta») y puerto para el analizador. |
| RF-03 | **No construido**: MediaPipe no cabe en Render gratis (DT-10, con plan). |

## Por qué se hizo así

1. **Datos sintéticos, dichos como tales.** No hay 1.000 reportes reales etiquetados
   (SUP-05). Un script (`scripts/ia/generar_datos_sinteticos.py`) arma reportes con plantillas
   y una semilla fija. Sirven para construir el camino completo (generar → entrenar → medir
   → exportar → servir), no para afirmar que el modelo acierta con reportes reales. La
   exactitud de 0,99 es esperable con plantillas y **no se debe presentar como resultado
   clínico**.
2. **Modelo pequeño y explicable.** TF-IDF + regresión logística: 61 KB, 0,05 ms por
   reporte y cada sugerencia se explica con las palabras que más pesaron (RNF-09). Un
   Transformer no cabría cómodo en 512 MB y sería difícil de explicar.
3. **scikit-learn solo para entrenar.** En producción se lee el JSON y se calcula con Python
   puro (`app/triaje/modelo.py`). Una prueba compara con scikit-learn.
4. **El modelo solo sube, nunca baja.** Las reglas ya protegen los críticos conocidos; el
   modelo, entrenado con datos sintéticos, no puede quitarles esa protección. Con la misma
   prioridad se conserva la confianza de las reglas, así un texto sin señales sigue yendo a
   revisión humana (RN-02).
5. **Recall de crítica (RNF-03).** El script baja el umbral de «crítica» hasta un recall de
   0,97 en validación, por margen sobre el 0,95 pedido: perder un crítico es peor que revisar
   uno de más.
6. **Compatibilidad con pesos a la vista.** No hay historial de adopciones exitosas para
   entrenar, así que es un puntaje con cinco factores que el refugio puede discutir. Solo
   mira el hogar y el animal (RNF-16); las pruebas lo comprueban.
7. **Algoritmo húngaro.** Repartir «el mejor para cada uno» en orden (voraz) puede bajar el
   total; el húngaro encuentra la mejor combinación en O(n³). Se verificó contra la fuerza
   bruta.
8. **La IA sugiere, la persona decide (RN-16).** La propuesta de jornada no aprueba nada; la
   compatibilidad no reemplaza la decisión del coordinador.

## Recorrido de una petición: un reporte con el modelo

1. El ciudadano envía `POST /reportes` con «Gato convulsionando en la calle 10».
2. `ServicioReportes` crea el reporte y llama a `ServicioTriaje.evaluar`, que ejecuta el
   clasificador con límite de 10 s (RN-03).
3. El clasificador es `clasificar_combinado` (`app/triaje/combinado.py`): corre las reglas
   (señal «convulsion» → crítica) y el modelo (`ModeloTriaje.clasificar`).
4. El modelo normaliza, cuenta palabras y pares que conoce, calcula TF-IDF, multiplica por
   los coeficientes de cada clase y aplica softmax. Si P(crítica) ≥ umbral, sugiere crítica.
5. `combinar` se queda con la más grave, junta las evidencias y asegura al menos 3.
6. `ServicioTriaje` aplica RN-02 y anota `version_modelo = "reglas-v0+tfidf-lr-v1"` (RF-20).

## Archivos a leer, en orden

1. `scripts/ia/generar_datos_sinteticos.py` y `scripts/ia/entrenar_triaje.py`.
2. `app/triaje/modelo.py`, `app/triaje/combinado.py`, `app/triaje/video.py`.
3. `app/adopciones/compatibilidad.py` y `app/adopciones/asignacion.py`.
4. En `app/api/main.py`: `triaje_por_defecto`, `/adopciones/recomendaciones`,
   `/refugio/jornada/propuesta`.
5. Pruebas: `test_modelo_triaje.py`, `test_compatibilidad.py`, `test_asignacion.py`,
   `test_video.py`.

## Cómo probarlo

```bash
pip install -r requirements-dev.txt          # incluye scikit-learn
python scripts/ia/entrenar_triaje.py         # vuelve a entrenar y escribe el JSON
pytest tests/test_modelo_triaje.py tests/test_asignacion.py -q
```

Para reentrenar con datos reales: exportar de la bitácora `decisiones_triaje` la
descripción y la `prioridad_final`, y usarlos en vez de `generar()` en `entrenar_triaje.py`.

## Preguntas de práctica para la sustentación

1. ¿Por qué el modelo puede subir la prioridad de las reglas pero no bajarla?
2. ¿Qué significa la exactitud de 0,99 con datos sintéticos y qué no significa?
3. ¿Cómo explica el sistema por qué sugirió «crítica»? ¿Qué es una evidencia?
4. ¿Por qué el algoritmo húngaro puede dar un total mayor que el voraz? Da un ejemplo.
5. ¿Qué atributos del adoptante no se usan en la compatibilidad y por qué?

### Respuestas

<details><summary>Respuesta 1</summary>

Porque el modelo se entrenó con datos sintéticos y las reglas ya están validadas para los críticos conocidos. Si pudiera bajar la prioridad, un error del modelo podría hacer que un caso crítico espere; subirla solo cuesta una revisión de más (RNF-03).

</details>

<details><summary>Respuesta 2</summary>

Significa que el modelo aprendió bien las plantillas con las que se generaron los datos. No significa que acierte con reportes reales escritos por ciudadanos: para eso hay que validarlo con reportes confirmados por veterinarios (DT-04).

</details>

<details><summary>Respuesta 3</summary>

Con al menos 3 evidencias (RNF-09): las palabras o pares de palabras que más empujaron hacia esa prioridad (por ejemplo «atropellado»), las señales de las reglas y, si faltan, lo que opinó cada parte. Una evidencia es una razón concreta que el veterinario puede revisar en el texto.

</details>

<details><summary>Respuesta 4</summary>

Porque el voraz elige en orden lo mejor para cada uno y puede quitarle a otro su mejor opción. Ejemplo de la prueba: Ana-animal 0 = 90, Ana-1 = 80, Beto-0 = 85, Beto-1 = 10. El voraz da 90 + 10 = 100; el húngaro da 80 + 85 = 165.

</details>

<details><summary>Respuesta 5</summary>

Edad, género, estrato, etnia, religión, discapacidad e ingresos: no se piden ni se usan. Son atributos protegidos o datos de ingresos (RNF-16, RF-08) y usarlos sería discriminar. Solo cuentan el hogar (vivienda, patio, niños, otros animales, horas solo, experiencia) y el animal.

</details>
