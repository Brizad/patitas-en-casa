# Trazabilidad de requisitos (ERS v5.0 → código, pruebas y PR)

Fuente de los requisitos: ERS final (Actividad Semana 2, versión 5.0). Estado al 29 de octubre
de 2026 (con la fase 6, v1.1.0), con `main` desplegado en https://patitas-en-casa-pnnk.onrender.com.

**Cómo leer la tabla.** *Hecho*: cumple lo que pide el ERS y hay una prueba que lo verifica.
*Parcial*: cumple lo esencial y se dice qué falta. *Pendiente*: no está construido; se explica
por qué. Los PR de las fases 1 a 5 se revisaron uno por uno (#66 a #107) y se integraron a
`main` juntos en el **#108**; por eso aparecen como «#NN → #108». Todas las rutas de pruebas
están en `tests/`.

Resumen: **RF: 32 hechos. RNF: 11 hechos, 4 parciales, 1 pendiente** (RNF-06), más RNF-15 que espera la decisión de Brayan. La fase 6 (#125) cerró RF-01, RF-03, RF-19 y RNF-02.

## Requisitos funcionales

| ID | Qué pide (resumido) | Estado | Código | Prueba | PR |
|----|---------------------|--------|--------|--------|----|
| RF-01 | Reporte sin cuenta: texto, ubicación, video opcional (60 s, 50 MB) y código | Hecho: el video se sube después del reporte con la misma clave, por partes y con la firma revisada (fase 6) | `app/reportes/servicio.py`, `app/api/video.py`, `app/video/almacen.py`, `app/pwa/reportar.js` | `test_reportes.py`, `test_api.py`, `test_video_api.py`, `test_pwa.py` | inc. 1, #62, #131, #136 |
| RF-02 | Prioridad sugerida con confianza y evidencias | Hecho | `app/triaje/` (`clasificador.py`, `modelo.py`, `combinado.py`) | `test_clasificador.py`, `test_modelo_triaje.py` | #96 → #108 |
| RF-03 | Analizar el video y la pose del animal | Hecho con un **trabajador local**: MediaPipe Object Detector + DeepLabCut SuperAnimal-Quadruped + medidas de la marcha + MLP. Modelo con datos sintéticos (nota 2) | `servicios/video/`, `app/video/` | `test_video_marcha.py`, `test_video_clasificador.py`, `test_video_analisis.py`, `test_video_trabajador.py`, `test_video_nodo.py`, flujo «Video: prueba de humo» | #126 a #142; instalador #143 |
| RF-04 | Cola por prioridad; confirmar o modificar con justificación | Hecho | `app/reportes/confirmacion.py`, `ordenar_cola` | `test_confirmacion.py`, `test_fechas_y_justificacion.py` | inc. 2, #77 → #108 |
| RF-05 | Notificar a los rescatistas de la zona (crítico o alto) | Hecho (el envío real necesita SMTP, nota 3) | `app/rescates/servicio.py`, `app/avisos/` | `test_rescates_zona.py`, `test_avisos_procesador.py` | #58, #64 |
| RF-06 | Ingreso con ficha: especie, salud, tratamientos, vacunas, esterilización | Hecho | `app/cupos/servicio.py`, `app/cupos/fichas.py` | `test_cupos.py`, `test_ficha_clinica.py` | inc. 1, #81 → #108 |
| RF-07 | Ocupación por refugio y alerta al 90 % a **sus** coordinadores | Hecho | `cupos_de` en `app/api/main.py`, `ServicioCupos` | `test_cupos_por_refugio.py`, `test_brechas_ers.py` | #80 → #108, #108 |
| RF-08 | Perfil del adoptante sin datos de ingresos | Hecho | `app/adopciones/modelos.py` | `test_adoptante_perfil.py` | #86 → #108 |
| RF-09 | Recomendar con puntaje y al menos 3 factores | Hecho | `app/adopciones/compatibilidad.py` | `test_compatibilidad.py` | #97 → #108 |
| RF-10 | Seguimiento a 30, 90 y 180 días, con devoluciones y su motivo | Hecho | `app/adopciones/servicio.py` | `test_seguimientos.py`, `test_visita_y_devolucion.py` | #90 → #108, #114 |
| RF-11 | Consultar el estado con el código, sin datos personales | Hecho | `app/reportes/seguimiento.py` | `test_seguimiento.py` | #53 |
| RF-12 | Guardar sin conexión y reenviar sin duplicar | Hecho | `app/pwa/reportar.js`, `Idempotency-Key` | `test_pwa.py`, `test_repositorio_contrato.py` | #62 |
| RF-13 | Autenticación (JWT) y permisos por rol, 6 roles | Hecho (JWT; sin proveedor OIDC externo) | `app/seguridad/tokens.py`, `app/api/seguridad.py` | `test_autenticacion.py`, `test_brechas_ers.py` | inc. 2, #108 |
| RF-14 | Refugios (nombre, dirección, capacidad) y su personal | Hecho | `app/refugios/` | `test_admin_refugios.py`, `test_brechas_ers.py` | #70 → #108, #108 |
| RF-15 | Disponibilidad y zona del rescatista | Hecho | `app/rescates/servicio.py` | `test_rescates.py`, `test_rescates_zona.py` | #50, #58 |
| RF-16 | Suspender o reactivar cuentas e historial de acceso | Hecho | `app/usuarios/servicio.py`, `GET /admin/usuarios/{correo}/accesos` | `test_admin_cuentas.py`, `test_brechas_ers.py` | #69 → #108, #108 |
| RF-17 | Posible duplicado a < 200 m y < 2 h | Hecho | `app/reportes/duplicados.py`, `app/reportes/descarte.py` | `test_duplicados.py`, `test_descarte.py` | #79, #78 → #108 |
| RF-18 | Contacto opcional del ciudadano, con autorización | Hecho (cifrado AES-256-GCM) | `app/seguridad/cifrado.py` | `test_contacto_ciudadano.py` | #112 |
| RF-19 | Fusionar texto y video; gana la más alta; registrar la discrepancia | Hecho: `aplicar_video` al recibir el resultado; la discrepancia se guarda y se ve en el panel; nunca cambia lo que decidió el veterinario | `app/triaje/video.py`, `app/video/servicio.py`, `panel/src/VideoDelReporte.tsx` | `test_video.py`, `test_video_trabajos.py`, `test_video_api.py` | #100 → #108, #130, #136 |
| RF-20 | Versión del modelo y prioridad confirmada como etiqueta | Hecho | `version_modelo` en reportes y decisiones | `test_version_modelo.py` | #77 → #108 |
| RF-21 | Aceptar el rescate: queda solo para ese rescatista | Hecho | `app/rescates/` (índices únicos parciales) | `test_rescates.py`, `test_rescates_contrato.py` | #50 |
| RF-22 | Registrar el resultado del rescate | Hecho | `app/rescates/servicio.py` | `test_rescates.py` | #50 |
| RF-23 | Escalar al coordinador a los 15 / 30 min | Hecho | `app/rescates/escalamiento.py` | `test_rescates_zona.py` | #58 |
| RF-24 | Actualizar la ficha clínica conservando el historial | Hecho | `app/cupos/fichas.py` | `test_ficha_clinica.py` | #81 → #108 |
| RF-25 | Publicar para adopción con restricciones y fotos | Hecho | `app/adopciones/`, `app/adopciones/fotos.py` | `test_publicacion.py`, `test_fotos.py` | #87 → #108, #116 |
| RF-26 | Egresos que liberan el cupo | Hecho | `egresar` en `app/cupos/repositorio*.py` | `test_egresos.py` | #82 → #108 |
| RF-27 | Solicitar; aprobar, rechazar con motivo o pedir visita | Hecho | `app/adopciones/servicio.py`, `reglas.py` | `test_solicitudes.py`, `test_decision_adopcion.py`, `test_visita_y_devolucion.py` | #88, #89 → #108, #114 |
| RF-28 | Asignación global en jornadas | Hecho | `app/adopciones/asignacion.py` | `test_asignacion.py` | #98 → #108 |
| RF-29 | Compromiso con datos del animal, del adoptante y del refugio | Hecho | `app/adopciones/compromiso.py`, `app/documentos/pdf.py` | `test_compromiso_pdf.py`, `test_brechas_ers.py` | #91 → #108, #108 |
| RF-30 | Indicadores: tiempos por prioridad, ocupación, adopciones, devoluciones, precisión | Hecho | `app/indicadores/calculo.py` | `test_indicadores.py`, `test_indicadores_completos.py` | #104 → #108, #118 |
| RF-31 | Exportar reportes, fichas e indicadores (CSV y PDF) anonimizados | Hecho | `app/indicadores/exportar.py` | `test_exportar.py`, `test_indicadores_completos.py` | #105 → #108, #118 |
| RF-32 | Bitácora inmutable | Hecho | `app/bitacora/`, migración `0020` | `test_bitacora.py` | #103 → #108 |

## Requisitos no funcionales

| ID | Qué pide | Estado y evidencia | Dónde | PR |
|----|----------|--------------------|-------|----|
| RNF-01 | Prioridad en ≤ 3 s (p95) con 30 reportes concurrentes, 500 reportes | Hecho **en local**: p95 = 2,84 s, 0 errores. En Render no se midió (nota 4) | `scripts/operacion/prueba_carga.py` | #120 |
| RNF-02 | Video de 60 s en ≤ 3 min | Hecho en la prueba de humo: 36 a 82 s por video, incluida la carga de los modelos (CPU de GitHub Actions, `fase-6-video.md`). En la PC del equipo depende de su CPU | `servicios/video/patitas_video/analisis.py` | #135, #137 |
| RNF-03 | Recall ≥ 0,95 en crítica con datos de veterinarios; RN-02 | Parcial: 0,98 con datos **sintéticos**; RN-02 hecho. Falta el conjunto de veterinarios (DT-04) | `scripts/ia/`, `test_modelo_triaje.py`, `test_servicio_triaje.py` | #96 → #108 |
| RNF-04 | Disponibilidad del 99 %, sondeo cada minuto | Parcial: sondeo cada 10 min (`sondeo.yml`, primera ejecución en verde). El plan gratis se duerme tras 15 min sin visitas: el 99 % exige un plan pagado | `.github/workflows/sondeo.yml` | #120 |
| RNF-05 | TLS ≥ 1.2, Argon2id, RBAC, bloqueo tras 5 intentos, ZAP sin altos | Hecho: TLS 1.0/1.1 rechazados y 1.2 aceptado (medido en Render); ZAP: **0 altos**; de 5 advertencias bajas quedan 3 informativas tras #122 (COEP y caché) | `zap.yml`, `test_limite_intentos.py`, `test_cabeceras.py` | inc. 2, #120, #122 |
| RNF-06 | 80 % reporta en ≤ 90 s; SUS ≥ 70 | **Pendiente**: necesita 10 participantes reales (nota 5) | — | — |
| RNF-07 | PWA en Android 8 / 2 GB; carga inicial ≤ 1,5 MB | Hecho: la PWA pesa **28 KB** y el panel 61 KB (medido en Render); gzip desde #122. No se probó en un teléfono físico | `app/pwa/` | #60, #122 |
| RNF-08 | Datos personales cifrados (AES-256); minimización | Parcial: el contacto del ciudadano y el perfil del adoptante (#149) van con AES-256-GCM y se piden datos mínimos; los correos de las cuentas no se cifran porque son el usuario con el que se inicia sesión (nota 6) | `app/seguridad/cifrado.py` | #112 |
| RNF-09 | ≥ 3 evidencias o factores | Hecho | `app/triaje/combinado.py`, `compatibilidad.py` | #96, #97 → #108 |
| RNF-10 | Cobertura ≥ 70 %, complejidad ≤ 10, ruff | Hecho: cobertura del 97 %; complejidad ≤ 10 en el CI (ruff C901) | `pyproject.toml`, `.github/workflows/ci.yml` | #108 |
| RNF-11 | WCAG 2.2 AA (contraste, teclado, lectores, objetivos ≥ 24 px) | Parcial: **medido** con axe-core y Lighthouse en cada PR (todas las pantallas y roles, claro, oscuro y 320 px): 0 fallas y Lighthouse 100 después de corregir 2 fallas del panel (`accesibilidad.md`). Teclado revisado a mano (#122). Falta escuchar el recorrido con un lector de pantalla | `panel/src/`, `app/pwa/` | #84 → #108, #122 |
| RNF-12 | Bitácora con actor, fecha, valor anterior y nuevo, sin edición | Hecho (#149): actor, fecha, acción, objeto y, en los cambios importantes, el valor anterior y el nuevo (prioridad, estado del reporte, cuenta activa, refugio, solicitud, ocupación; del perfil solo los campos). Inmutable por disparador. No guarda valores personales | `app/bitacora/` | #103 → #108 |
| RNF-13 | Docker, PostgreSQL 16, configuración por entorno | Hecho (Redis no hace falta: el outbox usa PostgreSQL) | `Dockerfile`, `render.yaml` | #64 |
| RNF-14 | 200 reportes/hora y 50 usuarios del panel | Hecho en local: ≈ 58.000 reportes/hora con 50 usuarios del panel a la vez | `scripts/operacion/prueba_carga.py` | #120 |
| RNF-15 | Respaldo diario cifrado; RPO ≤ 24 h, RTO ≤ 4 h | **Pendiente**: decisión de Brayan (nota 7) | — | — |
| RNF-16 | Sin atributos protegidos; tasa de recomendación por segmento | Hecho | `compatibilidad.py`, `calculo.py` | #97 → #108, #118 |

## Notas: lo que no se pudo y por qué

1. **Subir el video (RF-01), resuelto en la fase 6.** El video no se guarda en la base ni en
   un almacenamiento de objetos: espera en el disco temporal de Render solo hasta que el
   trabajador local lo analiza (minutos) y se borra. Si Render se reinicia antes, el trabajo
   queda «fallido» y manda el texto.
2. **Análisis de video (RF-03, RNF-02), resuelto en la fase 6 con un trabajador local.** No
   cabe en Render gratis y Hugging Face cobra los Spaces Docker, así que corre en una PC del
   equipo que le pide los videos a la API. Límites dichos claro: la red se entrenó con medidas
   **sintéticas** (DT-04), los pesos de SuperAnimal son de uso académico y en Windows directo
   el Control inteligente de aplicaciones bloquea DLL de torchvision (por eso WSL2). Ver
   `fase-6-video.md`.
3. **Correo real (RF-05, RF-18).** Sin `PATITAS_SMTP_HOST` los avisos quedan en el log y en la
   app (`GET /reportes/{codigo}/avisos`). Configurar un SMTP (por ejemplo, una cuenta de
   Gmail con contraseña de aplicación) lo hace Brayan.
4. **Carga en Render (RNF-01, RNF-14).** No se corrió contra la base real para no llenarla de
   reportes falsos. Con 0,1 CPU, el plan gratis será más lento que la laptop.
5. **Usabilidad (RNF-06).** Necesita personas reales y un cronómetro: es trabajo de campo de
   Brayan (el guion de la demostración sirve de tarea).
6. **Cifrado en reposo (RNF-08).** Render informa que cifra el disco de sus bases, pero eso no
   se pudo verificar desde aquí; el cifrado propio de la aplicación cubre el dato más sensible
   del ciudadano (su contacto).
7. **Respaldo (RNF-15).** Se preparó un flujo de GitHub Actions (copia diaria con `pg_dump`,
   cifrada con AES-256, con prueba de restauración), pero **no se integró**: saca una copia
   de los datos reales fuera de Render y esa decisión es de Brayan. Además, Render anuncia que sus
   bases gratis vencen al poco tiempo de creadas (revisa el aviso en tu panel de Render). Ver `preguntas-para-brayan.md` (P-07).

## Entregables de las tareas de cierre (después de la v1.1.0)

No son requisitos nuevos del ERS: mejoran la presentación y la operación de los que ya están.

| Entregable | Requisito que apoya | Dónde | Pruebas | Issue / PR |
|---|---|---|---|---|
| Scripts del nodo de video (WSL/Ubuntu) | RF-03, RNF-02 | `servicios/video/instalar_nodo.sh`, `arrancar_nodo.sh` | `test_video_nodo.py` | #143 / #144 |
| Página de inicio pública | RF-01 (entrada al reporte), RNF-07, RNF-11 | `app/inicio/` | `test_inicio.py` | #145 / #146 |
| Revisión de accesibilidad en el CI | RNF-11 | `scripts/accesibilidad/`, paso «Accesibilidad» del CI | `revisar.mjs` (axe-core + Lighthouse) | #147 / #148 |
| DT-09: registro de adoptantes con límite por IP y sin revelar correos | RNF-05, RNF-08 | `app/usuarios/intentos.py`, `POST /adoptantes` | `test_registro_adoptante.py` | #149 |
| Perfiles de adoptante cifrados | RNF-08 | `app/adopciones/repositorio_postgres.py`, migración `0026` | `test_perfiles_cifrados.py`, `test_adoptante_perfil.py` | #149 |
| Bitácora con valor anterior y nuevo | RNF-12 | `app/bitacora/`, `_cambio` en `app/api/main.py`, migración `0027` | `test_bitacora_valores.py` | #149 |
| Migración de la base a Neon (preparada, la ejecuta Brayan) | RNF-13, RNF-15 | `scripts/operacion/migrar_a_neon.py`, `docs/aprende/migrar-a-neon.md` | `test_migrar_a_neon.py`, `test_ajustes.py` | #154 / #155 |
| Manual de usuario con capturas por rol | RNF-06 (apoya la prueba con usuarios), RF de cada rol | `docs/manual-usuario.md`, `docs/manual/`, `scripts/accesibilidad/capturas.mjs` | capturas tomadas del sistema real con datos de demostración | #156 / #158 |
