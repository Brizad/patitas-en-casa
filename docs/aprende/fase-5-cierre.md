# Fase 5 · Cierre y v1.0.0

Issue #102. PR apilados: #103 → #104 → #105 → #106 → este (versión 1.0.0).

## Qué hace

| Requisito | Qué se construyó |
|-----------|------------------|
| RF-32, RNF-12 | Bitácora general inmutable: quién, qué, sobre qué y cuándo, de toda acción que cambia datos. |
| RF-30 | Indicadores: reportes, tiempos de confirmación, acuerdo por versión del modelo, rescates, ocupación, adopciones y seguimientos. |
| RF-31 | Exportar en CSV y PDF anonimizados. |
| Versión | 1.0.0 en la API, el panel y `pyproject.toml`; CHANGELOG con la sección `[1.0.0]`. |

## Por qué se hizo así

1. **Una bitácora para todo, en un solo lugar.** En vez de agregar una línea de registro en
   cada endpoint (y olvidar alguno), un *middleware* mira cada respuesta: si el método cambia
   datos y salió bien (2xx), la registra. Se guarda la **plantilla** de la ruta
   (`/refugio/animales/{animal_id}/egreso`) y sus parámetros, nunca el cuerpo: ahí van
   contraseñas y datos personales.
2. **Inmutable de verdad.** No basta con que el código no tenga «editar»: un disparador de
   PostgreSQL rechaza `UPDATE` y `DELETE` en la tabla `bitacora`. Si algún día un error o
   una persona intenta cambiar la historia, la base lo impide.
3. **Indicadores sin almacén de datos.** Con pocos datos, calcular al pedir es más simple y
   siempre está al día (lo dice el documento de arquitectura). Son funciones puras, fáciles
   de probar.
4. **El acuerdo por versión del modelo** cierra el círculo de la IA: si los veterinarios
   cambian mucho lo que sugiere una versión, esa versión no está ayudando.
5. **Anonimizar es quitar todo lo que identifique**, no solo el nombre: descripción
   (puede tener teléfonos), dirección, GPS (queda la comuna), hora (queda el día), código
   de seguimiento y correos.
6. **CSV seguro.** Una celda que empieza con `=` se ejecuta como fórmula al abrirla en Excel;
   se le antepone una comilla.

## Recorrido de una petición: un egreso queda en la bitácora

1. El coordinador registra un egreso: `POST /refugio/animales/7/egreso`.
2. FastAPI ejecuta los *middlewares* y luego el endpoint, que libera el cupo y responde 200.
3. Al volver, `registrar_en_bitacora` (en `app/api/main.py`) ve método POST y estado 200.
   Lee del token el correo (sin ir a la base), toma la plantilla de la ruta de
   `peticion.scope["route"]` y los parámetros (`{"animal_id": "7"}`).
4. En un hilo aparte (para no frenar otras peticiones) ejecuta
   `RepositorioBitacoraPostgres.registrar`, que hace un `INSERT`.
5. Si ese `INSERT` fallara, el egreso ya ocurrió: no se le dice al usuario que falló, se
   escribe en el log.
6. El administrador lo ve en «Indicadores → Bitácora».

## Archivos a leer, en orden

1. `app/bitacora/repositorio.py` y `migraciones/versions/0020_bitacora.py` (el disparador).
2. `registrar_en_bitacora` en `app/api/main.py`.
3. `app/indicadores/calculo.py` y `app/indicadores/exportar.py`.
4. Pruebas: `test_bitacora.py`, `test_indicadores.py`, `test_exportar.py`.
5. Panel: `Indicadores.tsx`.

## Cómo probarlo

```bash
alembic upgrade head
pytest --cov=app        # 568 pruebas, cobertura 98 %
```

A mano: haz algunas acciones en el panel y entra como administrador a «Indicadores»: verás
la bitácora. Prueba en `psql`: `UPDATE bitacora SET actor = 'x';` debe fallar.

## Preguntas de práctica para la sustentación

1. ¿Por qué la bitácora se hace con un *middleware* y no en cada endpoint?
2. ¿Qué impide, en la base, que alguien borre una fila de la bitácora? ¿Y `TRUNCATE`?
3. ¿Por qué no se guarda el cuerpo de la petición?
4. ¿Qué datos se quitan al exportar y por qué no basta con quitar el nombre?
5. ¿Qué es la inyección de CSV y cómo se evita?
