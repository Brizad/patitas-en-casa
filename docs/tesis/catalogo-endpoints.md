<!-- Archivo generado por scripts/tesis/generar_docs.py: no se edita a mano. -->

# Catálogo de endpoints

90 rutas de la API, leídas de la app real (`crear_app`). **Quién** sale de `exigir_rol` (401 sin sesión, 403 con otro rol). **Códigos**: el de éxito, los que la ruta lanza con `HTTPException` (también en las funciones auxiliares que llama), 401/403 por la sesión, 422 si tiene parámetros o cuerpo que validar y, en el video, todos los que puede lanzar su servicio (`VideoRechazado`; no todos aplican a cada ruta). Además, cualquier petición con cuerpo de más de 1 MB recibe 413 (A-01). **Requisitos**: los que cita el código de la ruta.

| Método | Ruta | Quién | Códigos | Requisitos |
|---|---|---|---|---|
| POST | `/auth/token` | público | 200, 401, 403, 422, 429 | DT-02, DT-06 |
| GET | `/auth/yo` | cualquier sesión | 200, 401 | — |
| POST | `/auth/contrasena` | cualquier sesión | 200, 401, 403, 422, 429 | — |
| GET | `/admin/diagnostico/ip` | administrador | 200, 401, 403 | — |
| GET | `/admin/usuarios` | administrador | 200, 401, 403 | — |
| POST | `/admin/usuarios` | administrador | 201, 401, 403, 409, 422 | — |
| PUT | `/admin/usuarios/{correo}/activo` | administrador | 200, 401, 403, 404, 409, 422 | RF-16 |
| GET | `/admin/usuarios/{correo}/accesos` | administrador | 200, 401, 403, 422 | RF-16 |
| GET | `/admin/refugios` | administrador | 200, 401, 403 | — |
| POST | `/admin/refugios` | administrador | 201, 401, 403, 422 | RF-14 |
| PUT | `/admin/usuarios/{correo}/refugio` | administrador | 200, 401, 403, 404, 422 | — |
| POST | `/adoptantes` | público | 201, 422, 429 | DT-09 |
| GET | `/adoptantes/yo/perfil` | adoptante | 200, 401, 403 | — |
| PUT | `/adoptantes/yo/perfil` | adoptante | 200, 401, 403, 422 | — |
| POST | `/refugio/animales/{animal_id}/publicacion` | coordinador | 201, 401, 403, 409, 422 | RF-25 |
| PUT | `/refugio/animales/{animal_id}/publicacion` | coordinador | 200, 401, 403, 409, 422 | — |
| POST | `/refugio/animales/{animal_id}/publicacion/retiro` | coordinador | 200, 401, 403, 409, 422 | — |
| GET | `/adopciones/animales` | público | 200 | RN-14 |
| GET | `/adopciones/animales/{animal_id}/foto` | público | 200, 422 | — |
| POST | `/refugio/animales/{animal_id}/foto` | coordinador | 201, 401, 403, 413, 415, 422 | RF-25 |
| GET | `/adopciones/recomendaciones` | adoptante | 200, 401, 403 | RF-09, RN-05 |
| POST | `/adopciones/solicitudes` | adoptante | 201, 401, 403, 422 | RF-27, RN-10 |
| GET | `/adopciones/solicitudes/mias` | adoptante | 200, 401, 403 | — |
| GET | `/refugio/solicitudes` | coordinador | 200, 401, 403 | — |
| GET | `/refugio/jornada/propuesta` | coordinador | 200, 401, 403 | RF-28, RN-16 |
| POST | `/refugio/solicitudes/{solicitud_id}/decision` | coordinador | 200, 401, 403, 404, 422 | RF-10, RF-27, RN-05, RN-11 |
| POST | `/refugio/solicitudes/{solicitud_id}/visita` | coordinador | 200, 401, 403, 404, 422 | RF-27 |
| POST | `/refugio/solicitudes/{solicitud_id}/devolucion` | coordinador | 200, 401, 403, 404, 422 | RF-10, RN-13 |
| GET | `/refugio/seguimientos` | coordinador | 200, 401, 403 | RF-10 |
| POST | `/refugio/seguimientos/{seguimiento_id}` | coordinador | 200, 401, 403, 404, 409, 422 | — |
| GET | `/adopciones/solicitudes/{solicitud_id}/compromiso.pdf` | adoptante, coordinador | 200, 401, 403, 404, 409, 422 | RF-29 |
| GET | `/refugio/animales/{animal_id}/perfil-adopcion` | coordinador, veterinario | 200, 401, 403, 422 | — |
| PUT | `/refugio/animales/{animal_id}/perfil-adopcion` | coordinador, veterinario | 200, 401, 403, 413, 415, 422 | — |
| PUT | `/refugio/animales/{animal_id}/salud-adopcion` | veterinario | 200, 401, 403, 413, 415, 422 | — |
| GET | `/adopciones/coleccion` | público | 200 | RN-14 |
| POST | `/reportes/{codigo}/foto` | público | 201, 403, 409, 422 | — |
| POST | `/reportes` | público | 201, 422, 429 | A-02, RF-01, RF-12 |
| GET | `/reportes/{codigo}` | público | 200, 404, 422 | — |
| GET | `/reportes/{codigo}/seguimiento` | público | 200, 404, 422 | HU-08, RN-14 |
| GET | `/cola` | coordinador, veterinario | 200, 401, 403 | HU-02 |
| POST | `/reportes/{codigo}/confirmacion` | veterinario | 200, 401, 403, 404, 409, 422 | D-05, HU-02 |
| POST | `/reportes/{codigo}/descarte` | veterinario | 200, 401, 403, 404, 409, 422 | D-02 |
| GET | `/reportes/{codigo}/avisos` | coordinador, veterinario | 200, 401, 403, 422 | — |
| GET | `/reportes/{codigo}/decisiones` | coordinador, veterinario | 200, 401, 403, 422 | — |
| GET | `/veterinario/historial` | veterinario | 200, 401, 403 | D-02 |
| PUT | `/rescatistas/yo/disponibilidad` | rescatista | 200, 401, 403, 422 | — |
| PUT | `/rescatistas/yo/zona` | rescatista | 200, 401, 403, 422 | — |
| GET | `/rescatistas/yo` | rescatista | 200, 401, 403 | — |
| GET | `/rescates/ofertas` | rescatista | 200, 401, 403 | RF-23 |
| GET | `/rescates/mio` | rescatista | 200, 401, 403 | — |
| GET | `/rescates/historial` | rescatista | 200, 401, 403 | — |
| POST | `/rescates/{codigo}/aceptar` | rescatista | 200, 401, 403, 404, 409, 422 | — |
| POST | `/rescates/{codigo}/llegue` | rescatista | 200, 401, 403, 404, 409, 422 | — |
| POST | `/rescates/{codigo}/liberar` | rescatista | 200, 401, 403, 404, 409, 422 | — |
| POST | `/rescates/{codigo}/resultado` | rescatista | 200, 401, 403, 404, 409, 422 | — |
| PUT | `/rescates/{codigo}/ubicacion` | rescatista | 200, 401, 403, 404, 409, 422 | — |
| DELETE | `/rescates/{codigo}/ubicacion` | rescatista | 200, 401, 403, 404, 409, 422 | — |
| POST | `/rescates/{codigo}/simulacion` | rescatista | 202, 401, 403, 404, 409, 422 | — |
| POST | `/rescates/{codigo}/informe` | rescatista | 201, 401, 403, 404, 409, 413, 422 | — |
| GET | `/rescates/{codigo}/informe` | cualquier sesión | 200, 401, 403, 404, 422 | RN-14 |
| GET | `/rescates/informes` | coordinador, veterinario | 200, 401, 403 | — |
| GET | `/fotos/{foto_id}` | cualquier sesión | 200, 401, 403, 404, 422 | — |
| POST | `/refugio/ingresos` | coordinador | 201, 401, 403, 409, 422 | — |
| GET | `/refugio/animales` | coordinador, veterinario | 200, 401, 403 | — |
| GET | `/refugio/animales/{animal_id}` | coordinador, veterinario | 200, 401, 403, 404, 422 | — |
| POST | `/refugio/animales/{animal_id}/historial` | veterinario | 201, 401, 403, 404, 422 | — |
| POST | `/refugio/animales/{animal_id}/egreso` | coordinador | 200, 401, 403, 404, 409, 422 | RF-26 |
| GET | `/refugio/ocupacion` | coordinador, veterinario | 200, 401, 403 | — |
| GET | `/indicadores` | administrador, alcaldia, coordinador | 200, 401, 403 | RF-30 |
| GET | `/indicadores/publicos` | público | 200 | — |
| GET | `/indicadores/reportes.csv` | administrador, alcaldia, coordinador | 200, 401, 403 | RF-31 |
| GET | `/indicadores/fichas.csv` | administrador, alcaldia, coordinador | 200, 401, 403 | RF-31 |
| GET | `/indicadores/resumen.pdf` | administrador, alcaldia, coordinador | 200, 401, 403 | — |
| GET | `/bitacora` | administrador | 200, 401, 403, 422 | — |
| GET | `/` | público | 200 | — |
| POST | `/admin/piloto/participantes` | administrador | 201, 401, 403 | RNF-06 |
| GET | `/admin/piloto/resultados` | administrador | 200, 401, 403 | — |
| GET | `/admin/piloto/resultados.csv` | administrador | 200, 401, 403 | — |
| POST | `/piloto/reportes` | público | 201, 403, 404, 409, 410, 422, 503 | — |
| POST | `/piloto/resultados` | público | 201, 403, 404, 409, 410, 422, 503 | — |
| POST | `/reportes/{codigo}/video` | público | 202, 413, 415, 422, 503 | RF-01, RF-03 |
| POST | `/video/trabajos/reclamar` | trabajador de video | 200, 204, 401, 503 | — |
| GET | `/video/trabajos/{id_}/archivo` | trabajador de video | 200, 401, 403, 404, 409, 410, 422, 503 | — |
| POST | `/video/trabajos/{id_}/vista` | trabajador de video | 200, 401, 413, 415, 422, 503 | — |
| POST | `/video/trabajos/{id_}/resultado` | trabajador de video | 200, 401, 403, 404, 409, 410, 422, 503 | — |
| POST | `/video/trabajos/{id_}/fallo` | trabajador de video | 200, 401, 403, 404, 409, 410, 422, 503 | — |
| GET | `/video/nodo` | coordinador, veterinario | 200, 401, 403 | — |
| GET | `/reportes/{codigo}/video` | coordinador, veterinario | 200, 401, 403, 404, 422 | — |
| GET | `/reportes/{codigo}/video/tira.png` | coordinador, veterinario | 200, 401, 403, 404, 422 | — |
| GET | `/reportes/{codigo}/video/vista.mp4` | coordinador, veterinario | 200, 401, 403, 404, 422 | RN-14 |
