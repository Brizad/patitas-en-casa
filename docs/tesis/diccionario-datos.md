<!-- Archivo generado por scripts/tesis/generar_docs.py: no se edita a mano. -->

# Diccionario de datos

22 tablas, leídas de `app/bd/esquema.py` (la misma definición que usan las migraciones de Alembic). La descripción es el comentario del código; «—» quiere decir que el código no tiene comentario para esa columna.

## `bitacora`

RF-32 (#102): bitácora general. Solo INSERT: un disparador (migración 0020) rechaza UPDATE y DELETE.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | BIGINT | no | PK | — | — |
| `momento` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `actor` | TEXT | no | — | — | — |
| `accion` | TEXT | no | — | — | — |
| `objeto` | JSONB | no | — | `'{}'::jsonb` | — |
| `estado_http` | SMALLINT | no | — | — | — |
| `valor_anterior` | JSONB | sí | — | — | — |
| `valor_nuevo` | JSONB | sí | — | — | — |

## `intentos_fallidos`

DT-06: un fallo de inicio de sesión por fila. clave = "correo:<correo>" o "ip:<ip>".

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `clave` | TEXT | no | — | — | — |
| `ocurrido_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

Restricciones e índices: `ck_intentos_fallidos_clave`: `clave <> ''`; `ix_intentos_fallidos_clave_ocurrido_en`: índice (clave, ocurrido_en).

## `piloto`

RNF-06 (#258): piloto de usabilidad. Un participante anónimo por fila (P01, P02…); el reporte de prueba no se guarda en `reportes`. Solo segundos y respuestas del SUS, sin datos personales.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `codigo` | VARCHAR(4) | no | PK | — | — |
| `token_hash` | VARCHAR(64) | no | única | — | SHA-256, nunca el token |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `vence_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `reporte_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `segundos` | INTEGER | sí | — | — | — |
| `sus` | SMALLINT[] | sí | — | — | — |
| `respondido_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |

Restricciones e índices: `ck_piloto_segundos`: `segundos BETWEEN 1 AND 3600`; `ck_piloto_sus`: `sus IS NULL OR cardinality(sus) = 10`.

## `refugios`

DT-05: la ocupación vive en la base; el cupo se toma con un UPDATE condicional (RN-04).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `nombre` | TEXT | no | — | — | — |
| `capacidad` | INTEGER | no | — | — | — |
| `ocupados` | INTEGER | no | — | `0` | — |
| `direccion` | TEXT | sí | — | — | 108 (RF-14) |

Restricciones e índices: `ck_refugios_capacidad`: `capacidad > 0`; `ck_refugios_ocupados`: `ocupados BETWEEN 0 AND capacidad`.

## `reportes`

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `codigo` | VARCHAR(8) | no | PK | — | — |
| `descripcion` | TEXT | no | — | — | — |
| `latitud` | DOUBLE PRECISION | sí | — | — | — |
| `longitud` | DOUBLE PRECISION | sí | — | — | — |
| `direccion` | TEXT | sí | — | — | — |
| `video_segundos` | INTEGER | sí | — | — | — |
| `estado` | VARCHAR(20) | no | — | — | — |
| `prioridad` | VARCHAR(10) | sí | — | — | — |
| `confianza` | DOUBLE PRECISION | sí | — | — | — |
| `evidencias` | JSONB | no | — | `'[]'::jsonb` | — |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `comuna` | SMALLINT | sí | — | — | HU-06: comuna de Cúcuta, opcional |
| `clave_idempotencia` | VARCHAR(64) | sí | única | — | — |
| `version_modelo` | VARCHAR(40) | sí | — | — | 75) |
| `contacto_cifrado` | TEXT | sí | — | — | 111): AES-256-GCM, nunca en claro |

Restricciones e índices: `ck_reportes_comuna`: `comuna BETWEEN 1 AND 10`; `ck_reportes_confianza`: `confianza BETWEEN 0 AND 1`; `ck_reportes_descripcion`: `char_length(btrim(descripcion, E' \t\n\r')) >= 20`; `ck_reportes_estado`: `estado IN ('recibido', 'clasificado', 'requiere_revision', 'sin_clasificar', 'confirmado', 'descartado')`; `ck_reportes_prioridad`: `prioridad IN ('critica', 'alta', 'media', 'baja')`; `ck_reportes_ubicacion`: `(latitud IS NOT NULL AND longitud IS NOT NULL) OR direccion IS NOT NULL`; `ck_reportes_video`: `video_segundos >= 0`; `ix_reportes_creado_en`: índice (creado_en); `ix_reportes_estado`: índice (estado).

## `rescatistas`

HU-06: disponibilidad de los rescatistas (RF-15) y rescates (RN-08).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `correo` | TEXT | no | PK | — | — |
| `disponible` | BOOLEAN | no | — | `false` | — |
| `actualizado_en` | TIMESTAMP WITH TIME ZONE | no | — | `now()` | — |
| `comunas` | SMALLINT[] | no | — | `'{}'` | — |

Restricciones e índices: `ck_rescatistas_comunas`: `comunas <@ ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]::smallint[]`.

## `videos_trozos`

188: el video espera aquí, por trozos de 1 MB, mientras el trabajador local lo descarga. Así sobrevive a un reinicio de Render. Se borra al terminar el análisis o a las 6 horas (la base gratis de Neon tiene 1 GB: a lo sumo 5 videos de 50 MB a la vez = 250 MB).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `ruta` | VARCHAR(40) | no | PK | — | — |
| `orden` | INTEGER | no | PK | — | — |
| `datos` | BYTEA | no | — | — | — |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

Restricciones e índices: `ck_videos_trozos_tamano`: `octet_length(datos) <= 1048576`; `ix_videos_trozos_creado`: índice (creado_en).

## `vistas_trozos`

214 (cambia RNF-08): la vista previa del video (MP4 de 5 MB o menos, con el esqueleto dibujado) se guarda aparte del video original, que se sigue borrando al terminar el análisis. Se borra a los 7 días o al cerrarse el reporte.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `ruta` | VARCHAR(40) | no | PK | — | — |
| `orden` | INTEGER | no | PK | — | — |
| `datos` | BYTEA | no | — | — | — |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

Restricciones e índices: `ck_vistas_trozos_tamano`: `octet_length(datos) <= 1048576`; `ix_vistas_trozos_creado`: índice (creado_en).

## `analisis_video`

125 (RF-03, RF-19): un trabajo de análisis por video de reporte. El video vive en el disco temporal de Render solo hasta que el trabajador local lo analiza; aquí quedan las medidas.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `codigo` | VARCHAR(8) | no | FK → reportes.codigo única | — | — |
| `ruta` | TEXT | no | — | — | — |
| `bytes` | BIGINT | no | — | — | — |
| `estado` | VARCHAR(16) | no | — | — | — |
| `intentos` | SMALLINT | no | — | `0` | — |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `reclamado_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `terminado_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `prioridad` | VARCHAR(10) | sí | — | — | — |
| `confianza` | DOUBLE PRECISION | sí | — | — | — |
| `evidencias` | JSONB | no | — | `'[]'::jsonb` | — |
| `medidas` | JSONB | no | — | `'{}'::jsonb` | — |
| `version_modelo` | VARCHAR(40) | sí | — | — | — |
| `motivo` | TEXT | sí | — | — | — |
| `discrepancia` | BOOLEAN | no | — | `false` | — |
| `tira` | BYTEA | sí | — | — | — |
| `vista_ruta` | VARCHAR(40) | sí | — | — | 214: vista previa del veterinario (vistas_trozos) |
| `vista_bytes` | INTEGER | sí | — | — | — |
| `vista_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |

Restricciones e índices: `ck_analisis_video_estado`: `estado IN ('pendiente', 'enviado', 'terminado', 'no_concluyente', 'fallido')`; `ck_analisis_video_tamano`: `bytes <= 52428800`; `ck_analisis_video_tira`: `tira IS NULL OR octet_length(tira) <= 204800`; `ix_analisis_video_estado_creado`: índice (estado, creado_en).

## `animales`

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `refugio_id` | INTEGER | no | FK → refugios.id | — | — |
| `nombre` | TEXT | no | — | — | — |
| `especie` | VARCHAR(10) | no | — | — | — |
| `estado_salud` | TEXT | no | — | — | — |
| `vacunado` | BOOLEAN | no | — | `false` | — |
| `esterilizado` | BOOLEAN | no | — | `false` | — |
| `ingresado_en` | TIMESTAMP WITH TIME ZONE | no | — | `now()` | — |
| `egresado_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `motivo_egreso` | VARCHAR(15) | sí | — | — | — |

Restricciones e índices: `ck_animales_egreso_completo`: `(egresado_en IS NULL) = (motivo_egreso IS NULL)`; `ck_animales_especie`: `especie IN ('perro', 'gato')`; `ck_animales_motivo_egreso`: `motivo_egreso IN ('adopcion', 'traslado', 'fallecimiento', 'devuelto')`.

## `avisos`

63 (outbox, D-03): avisos a rescatistas guardados en la misma transacción que la confirmación y enviados después por el procesador de avisos.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `reporte_codigo` | VARCHAR(8) | no | FK → reportes.codigo | — | — |
| `destinatario` | TEXT | no | — | — | — |
| `mensaje` | TEXT | no | — | — | — |
| `estado` | VARCHAR(10) | no | — | — | — |
| `intentos` | INTEGER | no | — | `0` | — |
| `ultimo_error` | TEXT | sí | — | — | — |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `proximo_intento_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `reclamado_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `enviado_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |

Restricciones e índices: `ck_avisos_estado`: `estado IN ('pendiente', 'enviando', 'enviado', 'fallido')`; `ck_avisos_intentos`: `intentos >= 0`; `uq_avisos_reporte_destinatario_mensaje`: única (reporte_codigo, destinatario, mensaje); `ix_avisos_estado_proximo_intento`: índice (estado, proximo_intento_en).

## `decisiones_triaje`

HU-02: bitácora de confirmaciones y ajustes de prioridad (RN-06, RN-16).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `reporte_codigo` | VARCHAR(8) | no | FK → reportes.codigo | — | — |
| `veterinario` | TEXT | no | — | — | — |
| `prioridad_sugerida` | VARCHAR(10) | no | — | — | — |
| `prioridad_final` | VARCHAR(10) | no | — | — | — |
| `justificacion` | TEXT | sí | — | — | — |
| `decidido_en` | TIMESTAMP WITH TIME ZONE | no | — | `now()` | — |
| `version_modelo` | VARCHAR(40) | sí | — | — | 75) |

Restricciones e índices: `ck_decisiones_justificacion`: `prioridad_final = prioridad_sugerida OR (justificacion IS NOT NULL AND char_length(btrim(justificacion)) >= 10)`; `ck_decisiones_prioridad_final`: `prioridad_final IN ('critica', 'alta', 'media', 'baja')`; `ck_decisiones_prioridad_sugerida`: `prioridad_sugerida IN ('critica', 'alta', 'media', 'baja')`; `ix_decisiones_triaje_veterinario`: índice (veterinario, decidido_en).

## `descartes`

D-02 (#75): bitácora de reportes descartados (uno por reporte).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `reporte_codigo` | VARCHAR(8) | no | PK FK → reportes.codigo | — | — |
| `veterinario` | TEXT | no | — | — | — |
| `motivo` | VARCHAR(10) | no | — | — | — |
| `duplicado_de` | VARCHAR(8) | sí | FK → reportes.codigo | — | — |
| `justificacion` | TEXT | no | — | — | — |
| `descartado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

Restricciones e índices: `ck_descartes_justificacion`: `char_length(btrim(justificacion)) >= 10`; `ck_descartes_motivo`: `motivo IN ('falso', 'duplicado')`; `ix_descartes_veterinario`: índice (veterinario, descartado_en).

## `escalamientos`

HU-06 (#46, RF-23): reportes escalados al coordinador por no tener rescatista a tiempo. La llave primaria garantiza un solo aviso aunque varios procesos revisen a la vez.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `reporte_codigo` | VARCHAR(8) | no | PK FK → reportes.codigo | — | — |
| `escalado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

## `rescates`

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `reporte_codigo` | VARCHAR(8) | no | FK → reportes.codigo | — | — |
| `rescatista` | TEXT | no | — | — | — |
| `estado` | VARCHAR(12) | no | — | — | — |
| `resultado` | VARCHAR(20) | sí | — | — | — |
| `aceptado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `actualizado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `llegada_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |

Restricciones e índices: `ck_rescates_estado`: `estado IN ('en_camino', 'en_sitio', 'atendido', 'liberado')`; `ck_rescates_resultado`: `resultado IN ('trasladado', 'atendido_en_sitio', 'no_encontrado', 'fallecido')`; `ck_rescates_resultado_al_atender`: `(estado = 'atendido') = (resultado IS NOT NULL)`; `ix_rescates_rescatista`: índice (rescatista, aceptado_en); `uq_rescates_reporte_vigente`: índice único (reporte_codigo) donde `estado <> 'liberado'`; `uq_rescates_rescatista_activo`: índice único (rescatista) donde `estado IN ('en_camino', 'en_sitio')`.

## `usuarios`

DT-02: cuentas del personal. Solo se guarda el hash Argon2id de la contraseña.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `correo` | TEXT | no | — | — | — |
| `nombre` | TEXT | no | — | — | — |
| `rol` | VARCHAR(20) | no | — | — | — |
| `hash_contrasena` | TEXT | no | — | — | — |
| `activo` | BOOLEAN | no | — | `true` | — |
| `creado_en` | TIMESTAMP WITH TIME ZONE | no | — | `now()` | — |
| `refugio_id` | INTEGER | sí | FK → refugios.id | — | 67 (RF-14) |

Restricciones e índices: `ck_usuarios_correo_minusculas`: `correo = lower(correo)`; `ck_usuarios_rol`: `rol IN ('veterinario', 'coordinador', 'rescatista', 'administrador', 'adoptante', 'alcaldia')`.

## `fotos_animales`

RF-25 (#115): una foto por animal, en la base (el disco de Render gratis no persiste).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `animal_id` | INTEGER | no | PK FK → animales.id | — | — |
| `tipo` | VARCHAR(12) | no | — | — | — |
| `datos` | BYTEA | no | — | — | — |
| `guardada_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

Restricciones e índices: `ck_fotos_tamano`: `octet_length(datos) <= 307200`; `ck_fotos_tipo`: `tipo IN ('image/jpeg', 'image/png', 'image/webp')`.

## `historial_clinico`

RF-24 (#75): historial clínico; las notas solo se insertan.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `animal_id` | INTEGER | no | FK → animales.id | — | — |
| `autor` | TEXT | no | — | — | — |
| `tipo` | VARCHAR(15) | no | — | — | — |
| `texto` | TEXT | no | — | — | — |
| `registrada_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |

Restricciones e índices: `ck_historial_texto`: `btrim(texto) <> ''`; `ck_historial_tipo`: `tipo IN ('observacion', 'tratamiento', 'vacuna', 'procedimiento')`; `ix_historial_clinico_animal`: índice (animal_id).

## `perfiles_adoptante`

RF-08 (#85): perfil del adoptante, uno por cuenta. Datos mínimos (RNF-08, RNF-16). 149 (RNF-08): con PATITAS_CLAVE_DATOS el perfil va entero en datos_cifrados (AES-256-GCM) y las columnas en claro quedan vacías (migración 0026).

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `correo` | TEXT | no | PK FK → usuarios.correo | — | — |
| `vivienda` | VARCHAR(12) | sí | — | — | — |
| `tiene_patio` | BOOLEAN | sí | — | — | — |
| `hay_ninos` | BOOLEAN | sí | — | — | — |
| `otros_animales` | BOOLEAN | sí | — | — | — |
| `horas_solo_al_dia` | SMALLINT | sí | — | — | — |
| `experiencia` | BOOLEAN | sí | — | — | — |
| `acepta_seguimiento` | BOOLEAN | sí | — | — | — |
| `actualizado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `datos_cifrados` | TEXT | sí | — | — | — |

Restricciones e índices: `ck_perfiles_claro_o_cifrado`: `datos_cifrados IS NOT NULL OR (vivienda IS NOT NULL AND tiene_patio IS NOT NULL AND hay_ninos IS NOT NULL AND otros_animales IS NOT NULL AND horas_solo_al_dia IS NOT NULL AND experiencia IS NOT NULL AND acepta_seguimiento IS NOT NULL)`; `ck_perfiles_horas`: `horas_solo_al_dia BETWEEN 0 AND 24`; `ck_perfiles_vivienda`: `vivienda IN ('casa', 'apartamento', 'finca')`.

## `publicaciones`

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `animal_id` | INTEGER | no | PK FK → animales.id | — | — |
| `descripcion` | TEXT | no | — | — | — |
| `tamano` | VARCHAR(10) | no | — | — | — |
| `energia` | VARCHAR(10) | no | — | — | — |
| `edad_meses` | SMALLINT | no | — | — | — |
| `apto_ninos` | BOOLEAN | no | — | — | — |
| `apto_otros_animales` | BOOLEAN | no | — | — | — |
| `necesita_patio` | BOOLEAN | no | — | — | — |
| `estado` | VARCHAR(12) | no | — | — | — |
| `publicado_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `carino` | SMALLINT | sí | — | — | — |
| `energia_nivel` | SMALLINT | sí | — | — | — |
| `juego` | SMALLINT | sí | — | — | — |
| `calma` | SMALLINT | sí | — | — | — |
| `etiquetas` | VARCHAR(20)[] | sí | — | — | — |
| `peso_kg` | NUMERIC(5, 2) | sí | — | — | — |
| `peso_adulto_kg` | NUMERIC(5, 2) | sí | — | — | — |

Restricciones e índices: `ck_publicaciones_calma`: `calma BETWEEN 0 AND 100`; `ck_publicaciones_carino`: `carino BETWEEN 0 AND 100`; `ck_publicaciones_edad`: `edad_meses BETWEEN 0 AND 360`; `ck_publicaciones_energia`: `energia IN ('baja', 'media', 'alta')`; `ck_publicaciones_energia_nivel`: `energia_nivel BETWEEN 0 AND 100`; `ck_publicaciones_estado`: `estado IN ('disponible', 'adoptado', 'retirada')`; `ck_publicaciones_etiquetas`: `cardinality(etiquetas) <= 3`; `ck_publicaciones_juego`: `juego BETWEEN 0 AND 100`; `ck_publicaciones_peso`: `peso_kg > 0 AND peso_kg <= 150`; `ck_publicaciones_peso_adulto`: `peso_adulto_kg > 0 AND peso_adulto_kg <= 150`; `ck_publicaciones_tamano`: `tamano IN ('pequeno', 'mediano', 'grande')`.

## `solicitudes`

RF-27 (#85): solicitudes de adopción.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `animal_id` | INTEGER | no | FK → publicaciones.animal_id | — | — |
| `adoptante` | TEXT | no | FK → usuarios.correo | — | — |
| `mensaje` | TEXT | no | — | — | — |
| `estado` | VARCHAR(10) | no | — | — | — |
| `creada_en` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `decidida_por` | TEXT | sí | — | — | — |
| `decidida_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `razon` | TEXT | sí | — | — | — |

Restricciones e índices: `ck_solicitudes_estado`: `estado IN ('pendiente', 'visita', 'aprobada', 'rechazada', 'devuelta')`; `uq_solicitudes_aprobada`: índice único (animal_id) donde `estado = 'aprobada'`; `uq_solicitudes_pendiente`: índice único (animal_id, adoptante) donde `estado = 'pendiente'`.

## `seguimientos`

RF-10 (#85): seguimientos a los 30, 90 y 180 días de la adopción.

| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |
|---|---|---|---|---|---|
| `id` | INTEGER | no | PK | — | — |
| `solicitud_id` | INTEGER | no | FK → solicitudes.id | — | — |
| `dia` | SMALLINT | no | — | — | — |
| `programado_para` | TIMESTAMP WITH TIME ZONE | no | — | — | — |
| `realizado_en` | TIMESTAMP WITH TIME ZONE | sí | — | — | — |
| `nota` | TEXT | sí | — | — | — |
| `registrado_por` | TEXT | sí | — | — | — |

Restricciones e índices: `ck_seguimientos_dia`: `dia IN (30, 90, 180)`; `uq_seguimientos_dia`: única (solicitud_id, dia).
