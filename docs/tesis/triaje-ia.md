# Triaje con IA: cómo se entrenó, qué se midió y qué no

> **Lo primero, sin rodeos.** El triaje **no está validado con datos reales**. El modelo se
> entrenó y se midió con textos **sintéticos** (generados por un programa) y con textos
> **escritos por el asistente**. Esos números sirven para encontrar fallas, no para afirmar
> RNF-03 (recall de «crítica» ≥ 0,95 **con datos de veterinarios**). RNF-03 está **pendiente**
> (DT-04) hasta correr `scripts/ia/validar_con_reales.py` con reportes confirmados.

## 1. Qué hace y quién decide

El triaje **sugiere**; **decide el veterinario** (RN-06). Cada reporte pasa por dos piezas y un
freno:

| Pieza | Qué es | Archivo |
|---|---|---|
| Reglas | Léxico de señales clínicas («no respira» → crítica, «cojea» → media…) con negación y normalización de ortografía | `app/triaje/clasificador.py`, `normalizacion.py` |
| Modelo | TF-IDF (palabras y pares) + regresión logística, leído de un JSON con Python puro | `app/triaje/modelo.py`, `modelo_tfidf_v1.json` |
| Combinación | **El modelo solo puede subir** la prioridad de las reglas, nunca bajarla | `app/triaje/combinado.py` |
| RN-02 | Confianza < 0,6 con prioridad media o baja → «requiere revisión» humana | `app/triaje/servicio.py` |
| RN-03 | Si el clasificador falla o tarda más de 10 s → prioridad alta, «sin clasificar» | `app/triaje/servicio.py` |

Por diseño, los errores se empujan hacia **revisar de más**, no hacia dejar una urgencia abajo.

## 2. Con qué se entrenó

- **4 000 reportes sintéticos**, 1 000 por prioridad, semilla 42
  (`scripts/ia/generar_datos_sinteticos.py`): plantillas con animal, señal clínica, lugar y
  ruido de escritura. **Ningún reporte real.** El archivo del modelo lo dice en su campo `datos`.
- 80 % para entrenar y 20 % para validar, estratificado. Después de entrenar, el umbral de
  «crítica» se baja hasta que el recall en esa validación llegue a 0,97.
- Se entrena con scikit-learn **solo** en `scripts/ia/entrenar_triaje.py`; producción no lo
  instala. Una prueba compara las probabilidades de Python puro con las de scikit-learn.

**Por qué no un Transformer (DT-04):** no cabe con la API en los 512 MB de Render gratis, y sin
datos reales no habría con qué afinarlo ni medirlo. TF-IDF + regresión logística responde en
milisegundos y cada sugerencia se explica con las palabras que más pesaron (RNF-09).

## 3. Qué se midió (y qué vale cada número)

| Medición | Resultado | Qué es | ¿Valida RNF-03? |
|---|---|---|---|
| Validación sintética (800 textos de la misma fuente) | exactitud 0,995; recall de crítica 0,98 | Guardado en `metricas_validacion` del JSON | **No**: el modelo vio textos de la misma fábrica |
| Sintéticos de otra semilla (400) | recall de crítica ≥ 0,95 (lo exige `test_modelo_triaje.py`) | Misma fábrica, otros textos | **No**, por la misma razón |
| 80 textos «como los escribe un ciudadano», antes de corregir | 54 aciertos (67,5 %); recall de crítica **0,76** (19 de 25) | Escritos por el asistente; etiqueta según el léxico de las reglas | **No** |
| Los mismos 80, después de corregir las reglas | 60 aciertos (75,0 %); recall de crítica 1,00 | Medido otra vez el 17-nov-2026 con `python -m scripts.ia.analizar_errores` | **No**: las correcciones salieron de esos mismos textos |
| 20 textos de control | 17 aciertos (85 %); recall de crítica 1,00 | Escritos después, por el mismo asistente | **No**: no son independientes |

El 0,76 es el número más honesto de la tabla: es lo que pasó la primera vez que el clasificador
vio textos que no salían de su propia fábrica. Con 25 casos críticos, además, el intervalo de
confianza del 95 % va de **0,57 a 0,89**: ni siquiera ese número es firme. Detalle caso por
caso: `docs/aprende/errores-ia-texto.md`.

## 4. Límites conocidos

1. **Sobre-triaje.** El modelo aprendió palabras sueltas de los sintéticos («gato», «perrita»)
   y sube a crítica textos tranquilos («gata que parió en mi garaje, están bien»). No deja
   urgencias abajo, pero llena la parte alta de la cola. De los 80 casos, 10 no críticos
   salieron como críticos.
2. **El léxico nunca está completo.** Una urgencia escrita de una forma que las reglas no
   conocen («se ahogó», «tieso») depende del modelo o de RN-02.
3. **La etiqueta de los casos escritos no es de un veterinario.** Sigue el criterio del
   léxico: mide la coherencia del sistema consigo mismo, no su acierto clínico.
4. **Solo español de la región y solo texto.** No se probó con audios transcritos, otros
   idiomas ni sarcasmo. El análisis de video es otro componente (`servicios/video/`), con sus
   propios umbrales sin validar por veterinarios.
5. **Sin datos reales no hay calibración:** la «confianza» es la probabilidad del modelo sobre
   datos sintéticos; no se sabe qué tan bien corresponde a aciertos reales.
6. **Sesgo de la fábrica:** los sintéticos reflejan lo que su autor creyó que escribiría un
   ciudadano. Lo que la gente escribe de verdad puede ser distinto.

## 5. Cómo se valida de verdad (el paso que falta)

Cada vez que un veterinario confirma o ajusta una prioridad, la decisión queda en
`decisiones_triaje` (prioridad sugerida, prioridad final, versión del modelo: RF-20). Esos son
los datos reales etiquetados. Cuando haya suficientes:

**1. Sacar el CSV (lo hace Brayan; solo lectura).** En el editor SQL de Neon, exportar a CSV:

```sql
SELECT r.descripcion, d.prioridad_final AS prioridad
FROM decisiones_triaje d JOIN reportes r ON r.codigo = d.reporte_codigo;
```

Los descartados (falsos o duplicados) no entran: no tienen decisión de prioridad. Guardar como
`datos_reales_triaje.csv` **fuera de git** (está en `.gitignore`): son textos escritos por
ciudadanos y pueden traer datos personales (Ley 1581). No se pega en issues ni en chats.

**2. Medir el clasificador actual:**

```bash
python -m scripts.ia.validar_con_reales datos_reales_triaje.csv
```

Imprime la matriz de confusión y un veredicto de RNF-03 que no hace trampa:

| Veredicto | Cuándo |
|---|---|
| «Aún no se puede saber» | Menos de 30 casos críticos, salga el recall que salga |
| «No cumple» | Recall de crítica < 0,95 |
| «Cumple en esta muestra» | Recall ≥ 0,95, pero el límite inferior del intervalo (Wilson, 95 %) baja de 0,95 |
| «Cumple» | El límite inferior del intervalo también es ≥ 0,95 |

Para dar una idea del tamaño: con 30 críticas y ningún fallo el límite inferior es 0,89; para
que llegue a 0,95 sin fallos hacen falta unas 73 críticas.

**3. Reentrenar (solo si hay datos suficientes):**

```bash
python -m scripts.ia.validar_con_reales datos_reales_triaje.csv --reentrenar
```

Aparta el 30 % de los reportes reales como **prueba** (ningún modelo los ve al entrenar),
entrena un candidato con los sintéticos más el 70 % real y compara candidato y actual sobre esa
misma prueba. Solo recomienda cambiar si el candidato cumple RNF-03, no halla menos críticas
que el actual y acierta más. **Nunca reemplaza el modelo publicado:** escribe
`modelo_triaje_candidato.json`; publicarlo es un PR aparte, con versión nueva (`tfidf-lr-v2`),
revisado por un veterinario y aprobado por Brayan.

**4. Solo entonces** se podría discutir que el modelo también **baje** prioridades (hoy solo
sube) o quitar el sobre-triaje (P-16). Antes no.

## 6. Qué decir en la sustentación

«El triaje combina reglas revisables con un modelo sencillo que solo puede subir la prioridad.
Lo entrenamos con datos sintéticos porque aún no hay reportes reales etiquetados; por eso sus
métricas no son una validación y RNF-03 está pendiente. Cuando lo probamos con textos distintos
a los sintéticos, el recall de crítica fue 0,76; corregimos las reglas y lo dijimos tal cual. El
sistema ya guarda cada decisión del veterinario y tiene listo el script que mide el recall real
con su intervalo de confianza y reentrena sin tocar el modelo publicado. Mientras tanto, quien
decide siempre es una persona.»
