# Fase 2 · Refugio completo

Issue #75. PR apilados: #76 → #77 → #78 → #79 → #80 → #81 → #82 → #83 → este. Se revisaron por separado y se integraron a `main` juntos en el **#108**.

## Qué hace

| Requisito | Qué se construyó |
|-----------|------------------|
| D-06 | Toda fecha de la API sale en UTC (`+00:00`) con `fecha_utc()`. |
| D-07 | La justificación exige 10 caracteres **y 5 letras**: «..........» ya no pasa. |
| RF-20, D-04 | `version_modelo` («reglas-v0») en cada reporte y en cada decisión de triaje. |
| D-02 | El veterinario descarta un reporte falso o duplicado, con justificación. |
| RF-17 | La cola marca posibles duplicados: con GPS, a ≤ 200 m y ≤ 2 h. |
| RF-14 (sigue) | Ingresos y ocupación del refugio de cada persona. |
| RF-06, RF-24 | Ficha clínica con historial de notas que solo crece. |
| RF-26 | Egreso con motivo que libera el cupo. |
| RF-07 | La alerta del 90 % ya nombra el refugio: queda por refugio. |
| D-08 | «Saltar a la cola» y foco de vuelta a la cola tras confirmar o descartar. |

## Por qué se hizo así

1. **Descartar es «la otra salida» de la cola.** Usa las mismas reglas que confirmar: solo el
   veterinario, una sola vez y con justificación. Los dos usan el mismo `UPDATE` condicional
   (`WHERE estado NOT IN ('confirmado', 'descartado')`): si uno confirma y otro descarta al
   mismo tiempo, PostgreSQL bloquea la fila y solo uno gana; el otro recibe 409.
2. **El ciudadano no ve el motivo del descarte** (RN-14): ve «Recibido → Descartado: revisado,
   no requiere una nueva atención». Decirle «falso» o darle el código del otro reporte no le
   sirve y expone información de otro ciudadano.
3. **Posibles duplicados: se señala, no se decide.** La IA y las reglas sugieren; la persona
   decide (RN-16). La distancia se calcula con la fórmula del haversine en Python porque hay
   pocos pendientes; con miles convendría PostGIS (índice espacial).
4. **Versión del modelo (RF-20).** Cuando las reglas se cambien por un modelo entrenado (fase
   4), la bitácora dirá qué versión sugirió cada prioridad. Las filas viejas quedan en NULL:
   no se inventa un dato que no se guardó.
5. **El historial clínico solo crece.** No hay endpoint para editar ni borrar notas; una
   corrección es otra nota. Así queda la traza de quién dijo qué y cuándo.
6. **Egreso seguro con concurrencia.** El animal solo se marca si `egresado_en IS NULL`; si
   dos personas registran el mismo egreso a la vez, solo una libera el cupo.
7. **Un repositorio por refugio.** `RepositorioCupos.para_refugio(id)` devuelve el mismo
   almacenamiento apuntando a otro refugio. Un animal de otro refugio «no existe» (404) para
   quien no trabaja allí.
8. **UTC en la API (D-06).** Guardar y transmitir en UTC evita confusiones; convertir a la
   hora de Cúcuta es trabajo de la pantalla (`toLocaleString()` en el panel).

## Recorrido de una petición: registrar un egreso

1. El coordinador abre la ficha en el panel (`Fichas.tsx`) y pulsa «Registrar egreso».
2. `egresar()` (`apiRefugio.ts`) envía `POST /refugio/animales/7/egreso` con
   `{"motivo": "adopcion"}` y su token.
3. FastAPI valida el motivo con `EgresoEntrada` (un `MotivoEgreso` desconocido da 422) y la
   dependencia `coordinacion` exige el rol (403 para el veterinario).
4. `registrar_egreso` (`app/api/main.py`) toma el repositorio del refugio del coordinador
   (`fichas_de`), comprueba que el animal esté allí (404) y llama a `egresar()`.
5. `RepositorioCuposPostgres.egresar` abre una transacción: `UPDATE animales ... WHERE id = 7
   AND refugio_id = 2 AND egresado_en IS NULL`; si no cambió ninguna fila, devuelve None
   (409). Si cambió, `UPDATE refugios SET ocupados = ocupados - 1` y devuelve la ocupación.
6. El panel muestra «el cupo quedó libre» y vuelve a pedir la ocupación y la lista.

## Archivos a leer, en orden

1. `app/reportes/confirmacion.py` (`validar_justificacion`) y `app/reportes/descarte.py`.
2. `app/reportes/duplicados.py`.
3. `app/triaje/servicio.py` (dónde se anota `version_modelo`).
4. `app/cupos/repositorio.py`, `repositorio_postgres.py` y `app/cupos/fichas.py`.
5. Migraciones `0012` a `0015`.
6. En `app/api/main.py`: `fecha_utc`, `cupos_de`, `fichas_de`, `/descarte`, `/refugio/animales`.
7. Pruebas: `test_fechas_y_justificacion.py`, `test_version_modelo.py`, `test_descarte.py`,
   `test_duplicados.py`, `test_cupos_por_refugio.py`, `test_ficha_clinica.py`,
   `test_egresos.py`.
8. Panel: `Descartar.tsx`, `Cola.tsx` (foco y duplicados), `Fichas.tsx`, `apiRefugio.ts`.

## Cómo probarlo

```bash
alembic upgrade head        # migraciones 0010 a 0015
pytest -q
cd panel && npm test && npm run build
```

A mano: con dos reportes con GPS casi iguales, la cola muestra «posible duplicado»; descarta
uno y consulta su seguimiento en `/app/` (debe decir «Descartado» sin el motivo). Como
coordinador registra un ingreso; como veterinario agrega una nota; como coordinador registra
el egreso y mira cómo baja la ocupación.

## Preguntas de práctica para la sustentación

1. ¿Qué pasa si un veterinario confirma y otro descarta el mismo reporte en el mismo segundo?
   ¿Qué línea de código lo impide?
2. ¿Por qué el seguimiento público no muestra el motivo del descarte ni el código original?
3. ¿Por qué se exige un mínimo de letras y no solo de caracteres? ¿Qué problema de la prueba
   con usuarios (E5) resuelve?
4. ¿Por qué el historial clínico no tiene endpoint para editar una nota? ¿Cómo se corrige un
   error?
5. ¿Qué haría falta para detectar duplicados con 100 000 reportes? ¿Por qué hoy no hace falta?

### Respuestas

<details><summary>Respuesta 1</summary>

Los dos ejecutan un `UPDATE reportes ... WHERE estado NOT IN ('confirmado', 'descartado')`. PostgreSQL bloquea la fila: el primero cambia el estado y el segundo ya no cumple la condición (0 filas), así que su servicio responde 409. La línea clave es la condición `PENDIENTE` en `RepositorioPostgres.confirmar` y `descartar`.

</details>

<details><summary>Respuesta 2</summary>

Por RN-14: la consulta pública solo muestra pasos y fechas. El motivo («falso») no le sirve al ciudadano y el código del original apunta al reporte de otra persona.

</details>

<details><summary>Respuesta 3</summary>

Porque «..........» tiene 10 caracteres y no explica nada. En la prueba con un compañero (E5) se vio que la justificación se podía llenar con relleno (D-07). Con 5 letras mínimas se acepta «Sangra mucho» y se rechaza el relleno.

</details>

<details><summary>Respuesta 4</summary>

Para conservar la traza de quién dijo qué y cuándo (RF-24, RF-32). Un error se corrige agregando otra nota que lo aclara; la nota equivocada queda, con su fecha y autor.

</details>

<details><summary>Respuesta 5</summary>

Un índice espacial (PostGIS) para buscar solo los reportes cercanos en vez de comparar todos contra todos. Hoy hay pocos reportes pendientes y el cálculo con la fórmula del haversine en Python tarda milisegundos.

</details>
