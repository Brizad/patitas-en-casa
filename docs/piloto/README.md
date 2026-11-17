# Piloto de usabilidad: material para las sesiones (RNF-06)

Todo lo que se imprime o se abre durante una sesión con una persona. **Aquí no hay
resultados**: los llena Brayan después de cada sesión. Nada de esta carpeta lleva nombres,
documentos ni teléfonos; cada persona es un código (`P01`, `P02`…).

| Archivo | Para qué | Cuándo |
|---|---|---|
| [`consentimiento.md`](consentimiento.md) | Consentimiento informado (se lee y se firma o se acepta de palabra) | Antes de empezar |
| [`tareas.md`](tareas.md) | Las 4 tareas, leídas tal cual: T1 reportar, T2 consultar, T3 el veterinario confirma, T4 el rescatista acepta | Durante |
| [`hoja-observacion.md`](hoja-observacion.md) | Una hoja por participante: qué logró, cuánto tardó, dónde dudó | Durante |
| [`sus.md`](sus.md) | Cuestionario SUS (10 frases) y su fórmula | Al terminar las tareas |
| [`plantilla.csv`](plantilla.csv) | Segundos de T1 y respuestas del SUS (lo lee `scripts/operacion/resultados_piloto.py`) | Después |
| [`plantilla-tareas.csv`](plantilla-tareas.csv) | Una fila por participante y tarea (completó, segundos, errores, ayudas) | Después |

## Orden de una sesión (unos 20 minutos)

1. Consentimiento (2 min).
2. T1 y T2 con cualquier persona; T3 solo con personal veterinario y T4 solo con rescatistas
   (o con quien haga ese papel: se anota en la hoja quién es de verdad).
3. Cuestionario SUS, antes de conversar sobre la prueba.
4. Dos preguntas abiertas de la hoja de observación y agradecer.

## Qué mide cada cosa (y qué no)

- **Metas del ERS (RNF-06):** 80 % o más de las personas completa **T1 en 90 segundos o
  menos**, y **SUS promedio de 70 o más**. Solo esas dos son metas.
- **T2, T3 y T4 no tienen meta en el ERS.** Se registran para saber si cada rol logra su
  tarea sin ayuda y dónde se traba; se reportan como observación, no como cumplimiento.
- Con menos de 10 personas el resultado es una estimación: se dice así en el informe.

## Cómo se hace sin ensuciar los datos reales

- **T1** con el **Modo piloto** del panel (pestaña del administrador → «Nuevo participante»):
  el reporte de prueba se valida como uno real pero no se guarda. Pasos en
  [`docs/aprende/piloto.md`](../aprende/piloto.md).
- **T2, T3 y T4** necesitan un reporte guardado. Antes de la sesión, Brayan crea **un reporte
  de práctica** desde `/app/` (descripción inventada, sin datos reales) y anota su código en
  una tarjeta. Al terminar el día, los reportes de práctica se descartan en el panel con el
  motivo «falso» y la justificación «Reporte de práctica del piloto de usabilidad».
- Las cuentas para T3 y T4 son las de demostración (`*@demo.patitas.co`), nunca la personal
  de alguien del refugio.

## Calcular

```bash
python scripts/operacion/resultados_piloto.py docs/piloto/resultados.csv
```

La fórmula del SUS está en [`sus.md`](sus.md). Si una meta no se cumple, no se esconde: se
escribe qué falló y se abre un issue con la mejora.
