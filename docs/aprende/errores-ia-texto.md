# Análisis de errores del triaje de texto (#245)

> **Aviso importante.** Los 100 textos de este análisis (80 + 20 de control) los **escribió el
> asistente (Claude)** imitando cómo escribe un ciudadano de Cúcuta por WhatsApp: con faltas de
> ortografía, abreviaturas («x», «q», «xfa»), sin tildes y con barrios reales. **No son
> reportes reales y no los etiquetó un veterinario.** Sirven para encontrar fallas del
> clasificador; **no** validan RNF-03 (recall ≥ 0,95 con datos de veterinarios), que sigue
> pendiente (DT-04).

## Método

- **Casos:** `scripts/ia/casos_ciudadanos_v1.json` (80: 25 críticos, 19 altos, 17 medios y
  19 bajos) y `scripts/ia/casos_ciudadanos_control.json` (20, escritos después de corregir).
- **Criterio de la etiqueta:** el del léxico de las reglas (`app/triaje/clasificador.py`) y las
  RN: **crítica** = riesgo de muerte inmediato (no respira, convulsiona, atropellado,
  inconsciente, hemorragia, envenenado, agonizando); **alta** = no se para, fractura, sangrado o
  herida; **media** = vómito, cojera, desnutrición, no come; **baja** = sarna, garrapatas o
  abandono sin lesión.
- **Clasificador evaluado:** el mismo que usa la API, reglas + modelo TF-IDF
  (`triaje_por_defecto`, versión `reglas-v0+tfidf-lr-v1`). Se mide la prioridad sugerida, antes
  de RN-02 (que manda a revisión humana los medios y bajos con confianza < 0,6).
- **Cómo repetirlo:** `python -m scripts.ia.analizar_errores` (o con la ruta del JSON de
  control).

## Resultado antes de corregir (80 casos)

Aciertos: 54 de 80 (67,5 %). **Recall de crítica: 0,76** (19 de 25). Dos críticas quedaron
como media o baja.

| Real \ Sugerida | crítica | alta | media | baja |
|---|---|---|---|---|
| crítica | **19** | 4 | 1 | 1 |
| alta | 4 | **14** | 1 | 0 |
| media | 1 | 4 | **12** | 0 |
| baja | 5 | 3 | 2 | **9** |

### Las 6 críticas que se escaparon (las fallas peligrosas)

| Texto (tal cual) | Sugerida | Por qué falló |
|---|---|---|
| «urgente perro con convulciones cada rato en el barrio motilones» | **baja** (0,30) | «convulciones» con c: el léxico solo tenía «convulsion» |
| «la perra esta como desmayada y con los ojos en blanco desde hace rato» | **media** | «desmayada» y «ojos en blanco» no estaban en el léxico |
| «gato no rrespira despues q lo golpearon, ayuda urgente» | alta | «rrespira»: el teclado del celular duplica la r |
| «perrito atropeyado x un taxi en el centro, chilla mucho y no se levanta» | alta | «atropeyado» con y |
| «perro electrocutado con un cable en el poste de la calle 8, quedo tirado» | alta | «electrocutado» no estaba |
| «perro tirado en la autopista atrapado entre los carros, sangra mucho y no se levanta» | alta | «sangra mucho» contaba como sangrado (alta), no como hemorragia |

Nota: la de «convulciones» sí habría llegado a un humano por RN-02 (confianza 0,30 → «requiere
revisión»), pero en la cola habría aparecido como baja, al final.

## Corrección (#245)

Solo en las reglas, que son las que puede revisar un veterinario; el modelo no se reentrenó:

- Léxico crítico nuevo: `convulc`, `atropey`, `desmay`, `ojos en blanco`, `electrocut`,
  `desangr`, `sangra mucho`, `mucha sangre`, `charco de sangre`.
- Léxico alto nuevo: `no se levanta`, `no se puede levantar`, `no puede caminar`.
- Normalización: una palabra que empieza por «rr» pierde una r («rrespira» → «respira»); en
  español ninguna palabra empieza así, y «perro» no cambia.
- Pruebas de regresión en `tests/test_clasificador.py` y `tests/test_normalizacion.py`. La
  negación sigue funcionando («no sangra mucho» no cuenta).

## Resultado después de corregir

| Conjunto | Aciertos | Recall de crítica | Críticas como media o baja |
|---|---|---|---|
| 80 casos, antes | 54 (67,5 %) | 0,76 | 2 |
| 80 casos, después | 60 (75,0 %) | **1,00** | 0 |
| 20 de control, antes | 16 (80 %) | 0,90 | 1 («una perrita desmayada…» → baja) |
| 20 de control, después | 17 (85 %) | **1,00** | 0 |

Matriz de los 80 casos después:

| Real \ Sugerida | crítica | alta | media | baja |
|---|---|---|---|---|
| crítica | **25** | 0 | 0 | 0 |
| alta | 4 | **14** | 1 | 0 |
| media | 1 | 4 | **12** | 0 |
| baja | 5 | 3 | 2 | **9** |

**Cuidado al leer estos números.** El 1,00 de los 80 casos es optimista: las correcciones salieron
de esos mismos textos. El conjunto de control se escribió después, pero lo escribió el mismo
asistente que ya conocía las palabras nuevas, así que tampoco es independiente. Solo un conjunto
real, etiquetado por veterinarios, dirá cuánto vale el recall.

## Errores que quedan (no se corrigieron, a propósito)

1. **El modelo sube a crítica textos tranquilos** (sobre-triaje): «gato negro q se metio en mi
   casa y no se quiere ir, esta bien» → crítica con 0,99; «gata que pario en mi garaje, ella y
   los gatitos estan bien» → crítica. Son 5 bajos, 4 altos y 1 medio sugeridos como críticos. El
   modelo se entrenó con textos sintéticos y aprendió palabras sueltas («gato», «perrita»); como
   la regla es «el modelo solo sube» (`app/triaje/combinado.py`), nada lo frena. **No es
   peligroso** (nunca baja una urgencia), pero llena la parte alta de la cola y el veterinario
   debe bajarla con justificación. Arreglarlo exige cambiar la regla de combinación o reentrenar:
   es decisión de Brayan (P-16) y necesita datos reales (DT-04).
2. **Medio ↔ alto:** «pata» y «perro» empujan al modelo hacia alta en cojeras leves («perro q
   renquea un poco de la pata de atras pero camina» → alta con 1,00).
3. **Bajos que no son bajos para el modelo:** «hongos en la piel», «sarna» con «piel» → media.
4. Palabras de urgencia que **aún no conoce** si se escriben de otra forma («convulsio», «se
   ahogo» sin «no respira», «tieso»). El léxico nunca estará completo: por eso RN-02 manda a
   revisión humana lo dudoso.

## ¿Y si se frena el modelo? (P-16, #285)

`MODELO_SUBE_MAX_NIVELES` (`app/config.py`) limita cuántos niveles sube el modelo sobre las
reglas; por defecto no hay tope. Se midió con los mismos casos:

| Tope | Aciertos (80) | Recall de crítica (80) | Recall de crítica (20 de control) | Críticas como media o baja |
|------|---------------|------------------------|-----------------------------------|----------------------------|
| Sin tope (hoy) | 60 | 1,00 | 1,00 | 0 |
| 2 niveles | 56 | 0,84 | 0,80 | 0 |
| 1 nivel | 55 | 0,80 | 0,80 | 4 (+2 en control) |

Frenar el modelo baja las falsas alarmas, pero también deja urgencias por debajo de crítica
cuando las reglas no conocen la palabra. Por eso queda apagado; la decisión es del autor.

## Qué decir en la sustentación

«Medimos con 80 textos escritos como los escribe un ciudadano, no con datos reales. Encontramos
6 urgencias que se escapaban por ortografía y vocabulario, las corregimos en las reglas con
pruebas de regresión y el recall de crítica en esos casos pasó de 0,76 a 1,00, pero ese número es
optimista. El error que queda es el contrario: el modelo exagera la gravedad de textos
tranquilos. Preferimos ese error, porque nunca deja una urgencia abajo, y lo resolveríamos con
datos reales etiquetados por veterinarios.»
