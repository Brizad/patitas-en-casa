# Piloto de usabilidad (RNF-06)

**Qué prueba.** Que una persona cualquiera envíe un reporte en **90 segundos o menos** y que
la aplicación se sienta fácil. Metas del ERS:

- **80 % o más** de los participantes reporta en ≤ 90 s.
- Puntaje **SUS promedio ≥ 70**.

Se necesitan unas **10 personas** que no hayan visto el sistema (familia, vecinos, compañeros
de otra carrera). Cada sesión dura unos 10 minutos.

## Antes de empezar (una sola vez)

1. Copia `docs/piloto/plantilla.csv` a `docs/piloto/resultados.csv` (una fila por persona,
   `P01` a `P10`). Si necesitas más personas, agrega filas.
2. Despierta el servicio: abre https://patitas-en-casa-pnnk.onrender.com/app/ unos minutos
   antes (el plan gratis tarda 30 a 60 s la primera vez; ese tiempo **no** debe contar).
3. Ten un celular con datos o wifi, un cronómetro y el cuestionario impreso (`docs/piloto/sus.md`).
4. No uses datos reales: la descripción es inventada y la ubicación puede ser una dirección cualquiera.

## La sesión, paso a paso (por persona)

1. **Saluda y explica** (30 s): «Estamos probando la aplicación, no a ti. Si algo te confunde,
   es culpa de la aplicación. Puedes parar cuando quieras». Pide permiso para anotar su tiempo
   y sus respuestas, sin su nombre (solo `P01`, `P02`…).
2. **Prepara el celular** con la página `/app/` ya abierta y la pantalla de inicio visible. No
   le muestres cómo se usa.
3. **Dale la tarea**, leída tal cual: «Vas por la calle y ves un perro atropellado frente al
   parque Santander que no se levanta y sangra mucho. Usa esta aplicación para reportarlo».
4. **Cronometra**: arranca cuando termine de leer la tarea y para cuando aparezca el **código
   del reporte** en pantalla. Anota los segundos.
5. **No ayudes.** Si se atasca, espera. Si pasan 3 minutos, detén la prueba y anota el tiempo
   real (180) y qué lo trabó; así cuenta como que no cumplió.
6. **Observa y anota** en el cuaderno dónde dudó, qué tocó por error y qué dijo en voz alta.
   Eso sirve para mejorar la aplicación aunque no entre en el CSV.
7. **Entrega el SUS** (`docs/piloto/sus.md`) apenas termine, antes de comentar nada. Que lo
   marque él o ella; si no puede, léelo sin opinar.
8. **Pasa los datos al CSV:** `segundos` y `sus_1` a `sus_10` tal como los marcó. No inviertas
   ninguna respuesta; el script lo hace.
9. **Agradece** y pregunta si algo le pareció confuso (solo para tu cuaderno).

## Calcular los resultados

```bash
python scripts/operacion/resultados_piloto.py docs/piloto/resultados.csv
```

Imprime cuántos cumplieron los 90 s, el porcentaje, el SUS promedio y si cada meta
**CUMPLE** o **NO CUMPLE**. Las filas vacías se ignoran; una fila a medias da un error que
dice cuál participante revisar.

## Cuidados

- `resultados.csv` no lleva nombres, documentos ni teléfonos (Ley 1581). Solo el código `P01`.
- Con menos de 10 personas el resultado es una estimación; dilo así en el informe.
- Si una meta no se cumple, no se esconde: se anota qué falló (por tus observaciones del
  paso 6) y se abre un issue con la mejora.
