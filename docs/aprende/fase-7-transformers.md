# Fase 7 · Triaje de texto con Transformers

Tarea 7 de cierre. Rama `feat/triaje-transformers` (commits pequeños, uno por PR).

## Qué se hizo

| Paso | Qué se construyó | Dónde |
|------|------------------|-------|
| Datos | Generador v2 de reportes **sintéticos** (8.200), con jerga, ruido y negaciones; prueba fija de 1.200 | `scripts/ia/datos_triaje.py`, `scripts/ia/datos/triaje_prueba.csv` |
| Afinado | mALBERT afinado en GitHub Actions, exportado a ONNX y cuantizado a int8 | `scripts/ia/entrenar_transformer.py`, `.github/workflows/entrenar-triaje.yml` |
| Comparación | Mismas métricas para reglas, TF-IDF y Transformer sobre la misma prueba | `scripts/ia/evaluar_triaje.py` |
| Memoria | RSS del proceso y tiempo por predicción | `scripts/ia/medir_memoria_triaje.py` |
| API | Adaptador ONNX con la misma forma que el TF-IDF, listo pero **apagado**: el modelo no está en el repositorio | `app/triaje/modelo_onnx.py`, `app/triaje/combinado.py` |

**Resultado en una línea:** el Transformer cabe en la memoria de Render, pero **no gana**: el
mismo TF-IDF reentrenado con los datos nuevos acierta más y se equivoca menos hacia crítica,
cientos de veces más rápido. La API sigue con reglas + TF-IDF.

## 1. Qué es un Transformer y qué es afinar

- El **TF-IDF** (fase 4) cuenta palabras: «atropellado» suma hacia crítica, «sarna» hacia
  baja. No sabe que «la moto lo levantó» y «lo atropellaron» dicen lo mismo, ni distingue
  bien «sangra» de «no sangra» si no vio ese par de palabras al entrenar.
- Un **Transformer** convierte cada pieza de palabra en un vector y, capa por capa, deja que
  cada pieza «mire» a las demás (*atención*). Así el vector de «sangra» cambia si antes hay un
  «no». Se **preentrena** con millones de textos adivinando palabras tapadas, y por eso ya
  trae una idea del idioma.
- **Afinar** (*fine-tuning*) es tomar ese modelo preentrenado, ponerle encima una capa nueva
  con 4 salidas (crítica, alta, media, baja) y seguir entrenando toda la red unas pocas
  épocas con nuestros reportes etiquetados. Se aprovecha lo que ya sabe del idioma y se le
  enseña solo la tarea.

## 2. Los datos (siguen siendo sintéticos: DT-04 abierta)

No hay reportes reales etiquetados por veterinarios. `scripts/ia/datos_triaje.py` arma
reportes con plantillas y una semilla fija (mismo resultado siempre):

- Frases por prioridad con jerga de Cúcuta: «la moto lo levantó y quedó tieso», «chandoso»,
  «gatico», «está en los puros huesos», barrios y avenidas de la ciudad.
- Ruido de WhatsApp: «q», «xq», «porfa», «ta», errores de letras, sin tildes, MAYÚSCULAS,
  emojis, puntuación de más o de menos.
- Negaciones de algo más grave que la etiqueta («no sangra», «ya no cojea»): enseñan que la
  palabra grave sola no basta.
- **Tres conjuntos sin textos repetidos:** entrenamiento (6.000), validación (1.000, para el
  umbral de crítica) y prueba (1.200, fija en el repositorio). La mitad de la prueba son
  **casos difíciles que el modelo nunca vio**: frases reservadas («lo volteó un camión y está
  privado», «tiene churrias»), negaciones nuevas («tampoco sangra», «ni cojea ni nada») y
  ruido fuerte.

Importante para la sustentación: aunque las frases difíciles son nuevas, todo sale del mismo
programa. Un buen número aquí **no** prueba que el modelo acierte con reportes reales.

## 3. El modelo elegido y su licencia

| Candidato | Licencia | ¿Sirve? |
|-----------|----------|---------|
| `dccuchile/albert-tiny-spanish` (ALBETO) | No declarada en el modelo ni en su repositorio | No: sin licencia no se puede redistribuir |
| `Geotrend/distilbert-base-es-cased` | Apache-2.0 | Sí, pero ~64 M de parámetros (~64 MB en int8) |
| **`cservan/multilingual-albert-base-cased-32k` (mALBERT)** | **Apache-2.0** | **Elegido**: ~12 M de parámetros porque ALBERT comparte una sola capa entre las 12 |

mALBERT (Servan et al., 2024, arXiv:2403.18338) se preentrenó con Wikipedia en 52 idiomas,
entre ellos el español. Se fija la revisión exacta del modelo base (`REVISION` en el script)
para que el entrenamiento se pueda repetir. La licencia Apache-2.0 permite usarlo,
modificarlo y redistribuirlo citando el origen: la cita va en `app/triaje/onnx/triaje_onnx.json`
y aquí.

## 4. ONNX y cuantización

- **ONNX** es un formato estándar para guardar una red ya entrenada. `onnxruntime` la ejecuta
  sin torch: la API instala ~20 MB en lugar de ~800 MB.
- **Cuantizar a int8** es guardar cada peso con 8 bits en vez de 32. El archivo pesa ~4 veces
  menos y en CPU suele ir más rápido; se pierde un poco de precisión, por eso **las métricas
  se miden con el modelo int8**, el mismo que se despliega.
- El **tokenizador** (`tokenizer.json`) parte el texto en piezas («atropellado» →
  «▁atrope», «llado») y las convierte en números. Lo ejecuta la librería `tokenizers`.

## 5. Resultados sobre la misma prueba fija (1.200 reportes)

Ejecución `40991986713` del flujo `entrenar-triaje.yml` (3 épocas, ~59 min de afinado). Se
comparan siete clasificadores; los que importan son los que usa o usaría la API («reglas +
modelo»). **TF-IDF v1** es el modelo publicado hoy (entrenado con los datos v1); **TF-IDF v2**
es el mismo método reentrenado con los datos v2, para comparar con justicia.

| Clasificador | Exactitud | F1 macro | Recall crítica | Precisión crítica | Recall crítica en frases nuevas | ms/reporte |
|---|---|---|---|---|---|---|
| reglas-v0 | 0,417 | 0,386 | 0,292 | 0,640 | 0,000 | 0,05 |
| tfidf-lr-v1 | 0,666 | 0,663 | 0,672 | 0,560 | 0,380 | 0,09 |
| **reglas + tfidf-lr-v1 (API hoy)** | 0,652 | 0,651 | 0,696 | 0,521 | 0,380 | 0,15 |
| tfidf-lr-v2 | **0,890** | **0,888** | 0,864 | **0,885** | 0,460 | 0,10 |
| reglas + tfidf-lr-v2 | 0,833 | 0,830 | 0,876 | 0,768 | 0,460 | 0,16 |
| malbert-onnx-v1 | 0,818 | 0,819 | 0,896 | 0,597 | 0,560 | 70,7 |
| reglas + malbert-onnx-v1 | 0,767 | 0,769 | **0,908** | 0,554 | **0,560** | 70,4 |

F1 por clase (reglas + modelo):

| | crítica | alta | media | baja |
|---|---|---|---|---|
| reglas + tfidf-lr-v1 | 0,596 | 0,646 | 0,664 | 0,700 |
| reglas + tfidf-lr-v2 | 0,819 | 0,855 | 0,795 | 0,852 |
| reglas + malbert-onnx-v1 | 0,688 | 0,806 | 0,780 | 0,802 |

Exactitud por tipo de caso (reglas + modelo): comunes 0,73 / 0,92 / 0,90; frases nuevas
0,27 / 0,47 / 0,33; negaciones 0,71 / 0,86 / 0,66; ruido fuerte 0,75 / 0,92 / 0,90 (TF-IDF v1 /
TF-IDF v2 / Transformer).

Matrices de confusión 4×4 (filas = prioridad real, columnas = la sugerida; orden crítica, alta,
media, baja; 250 + 350 + 300 + 300 reportes):

```
reglas + tfidf-lr-v1 (API hoy)    reglas + tfidf-lr-v2           reglas + malbert-onnx-v1
 174  42   8  26                   219   9   4  18                227  11   5   7
  81 218  20  31                    36 295  10   9                 73 265  11   1
  42  37 171  50                    17  31 215  37                 48  27 215  10
  37  28  16 219                    13   5  12 270                 62   5  20 213
```

Cómo leerlo:

- **Nadie llega a RNF-03 (0,95) en esta prueba difícil.** En los casos comunes sí: 0,99 con
  TF-IDF v2 y con el Transformer. Lo que falla son las frases que nunca vieron
  («está privado», «no coge aire»): ahí el mejor recall es 0,56.
- **El Transformer encuentra un poco más de críticos** (0,908 contra 0,876) y generaliza algo
  mejor a frases nuevas (0,56 contra 0,46), que es justo lo que se esperaba de él.
- **Pero lo paga caro:** para llegar a recall 0,97 en validación su umbral de crítica bajó
  hasta 0,10, y por eso marca como crítico a 62 reportes de prioridad baja y 73 de alta
  (precisión 0,55). Le van peor las negaciones (0,66 contra 0,86). Cada falso crítico es un
  veterinario y un rescatista movilizados sin necesidad.
- **Lo que más mejoró fueron los datos, no el modelo:** el mismo TF-IDF pasa de 0,652 a 0,833
  de exactitud solo por entrenarlo con los datos v2.

## 6. Memoria y tiempo medidos

`scripts/ia/medir_memoria_triaje.py` en el runner de GitHub (Linux, Python 3.12, 1 hilo de
onnxruntime), memoria residente (RSS) del proceso:

| Momento | MB |
|---|---|
| Python recién arrancado | 15,4 |
| App creada (repositorios en memoria, TF-IDF cargado, onnxruntime importado) | 129,6 |
| + modelo ONNX cargado | 209,4 |
| Tras clasificar las 1.200 frases de la prueba | 213,0 |
| **Pico (VmHWM)** | **216,5** → quedan **295,5 MB libres** de 512 |

Tiempo por predicción (reglas + Transformer): mediana 69 ms, p95 94 ms, máximo 117 ms. El
TF-IDF tarda 0,15 ms. En Render gratis la CPU es compartida y más lenta: se espera bastante más
que en el runner, aunque lejos de los 10 s de RN-03.

El modelo int8 pesa **40,8 MB** (tokenizador 2,3 MB). La cuantización dinámica apenas lo
redujo (48,1 MB en fp32): el ahorro esperado de ~4 veces no se dio. No se investigó la causa
(probablemente la capa compartida de ALBERT o los embeddings que el cuantizador no tocó).

## 7. Decisión de despliegue

- **Memoria: sí cabría** (216,5 MB de pico; se pedía dejar ≥ 150 MB libres y quedan 295).
- **Repositorio: no cabe** con la regla de < 25 MB (pesa 40,8 MB).
- **Calidad: no gana** al TF-IDF reentrenado: menos exactitud (0,767 contra 0,833 en reglas +
  modelo) y mucha menos precisión en crítica (0,554 contra 0,768), a cambio de 3 puntos de
  recall de crítica.

Por eso **la API sigue con reglas + TF-IDF v1** y el Transformer queda documentado como
opción, con todo listo para activarlo si un modelo futuro pasa la puerta:

1. El adaptador (`app/triaje/modelo_onnx.py`) y la carga en `triaje_por_defecto()` ya están en
   el código y probados con dobles. Si `app/triaje/onnx/triaje_onnx.json` **no existe** (hoy),
   no se importa onnxruntime y no gasta memoria.
2. Para activarlo: correr el flujo, comprobar que pasa `tests/test_triaje_transformer.py`
   (recall de crítica ≥ 0,95 en la prueba fija), poner los archivos del artefacto en
   `app/triaje/onnx/` (si pesa > 25 MB, descargarlos en el `Dockerfile` desde un release que
   cree Brayan) e instalar `requirements-transformer.txt`. La versión guardada pasa a
   `reglas-v0+malbert-onnx-v1` (RF-20).
3. `PATITAS_TRIAJE_TRANSFORMER=0` lo apaga sin desplegar código.

Recomendación para Brayan (no aplicada, porque cambia el modelo en producción): publicar el
**TF-IDF v2** (`python scripts/ia/entrenar_triaje.py --v2 app/triaje/modelo_tfidf_v2.json` y
apuntar `ARCHIVO` a ese JSON). En esta prueba sube el recall de crítica de la API de 0,696 a
0,876 sin costo de memoria ni de tiempo.

## 8. Reglas de seguridad que se conservan

- **El modelo solo sube** (`combinado.py`): si las reglas ven crítico, sigue crítico.
- **RN-02**: con la misma prioridad se conserva la confianza de las reglas; media o baja con
  confianza < 0,6 va a «requiere revisión».
- **RN-03**: si el Transformer lanza un error o tarda más de 10 s, `ServicioTriaje` aplica la
  falla segura (alta, sin clasificar, revisión manual). Si no **carga** al arrancar (falta
  onnxruntime, archivo dañado), la API sigue con reglas + TF-IDF y la versión guardada lo
  dice (RF-20). `PATITAS_TRIAJE_TRANSFORMER=0` vuelve al TF-IDF sin desplegar código.
- **RNF-03**: el umbral de crítica se baja en validación hasta recall 0,97.
- Pruebas: `tests/test_modelo_onnx.py` (dobles: normalización, umbral, solo sube, RN-02,
  RN-03 por error y por demora) y `tests/test_triaje_transformer.py` (modelo real).

## 9. Límites

- Datos sintéticos: los números no son clínicos. Falta reentrenar y validar con reportes
  reales confirmados (DT-04); la etiqueta ya la guarda la bitácora (RF-20).
- El Transformer no señala palabras como el TF-IDF; sus evidencias son las probabilidades.
  Las reglas siguen aportando las señales con nombre (RNF-09).
- El tiempo medido es en un servidor de GitHub; en Render gratis (CPU compartida) será mayor.
- Cada reentrenamiento cambia el umbral y las métricas: se repite la comparación antes de
  cambiar el modelo publicado.

## 10. Preguntas de práctica

1. **¿Por qué no se dejó que el Transformer baje la prioridad que dan las reglas?**
   Porque se entrenó con datos sintéticos. Si las reglas (validadas por un veterinario) ven
   un crítico, quitarle esa protección podría perder un animal grave (RNF-03). Ante la duda,
   se sube o se manda a revisión humana.
2. **¿Qué es cuantizar y por qué se evalúa el modelo cuantizado y no el original?**
   Guardar los pesos en 8 bits en vez de 32: en teoría el archivo pesa ~4 veces menos (aquí
   solo bajó de 48 a 41 MB). Cambia un poco
   los resultados, así que se mide el modelo que de verdad se despliega.
3. **¿Por qué ALBETO no, si es un modelo en español?** Porque ni su ficha ni su repositorio
   declaran licencia; sin licencia no hay permiso para redistribuirlo. mALBERT es Apache-2.0.
4. **Si mañana el modelo ONNX se corrompe en Render, ¿qué pasa con los reportes?**
   Al arrancar no carga: la API usa reglas + TF-IDF y guarda esa versión. Si falla al
   clasificar un reporte, ese reporte va a falla segura: alta, sin clasificar, revisión
   manual (RN-03).
5. **¿Por qué la prueba fija tiene frases que nunca se usan al entrenar?** Para medir si el
   modelo generaliza a formas nuevas de decir lo mismo, que es lo que pasará con reportes
   reales. Con frases ya vistas, cualquier modelo parece excelente.
