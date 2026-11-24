# Sustentación final · Patitas en Casa

Guía para defender el proyecto. Cada afirmación apunta al archivo que la demuestra: si el jurado
pregunta «¿dónde está eso?», se abre ese archivo. Sin cifras que no estén en el repositorio.

## 1. Arquitectura, capa por capa

Imagen: `docs/arquitectura.svg`. Detalle C4: `docs/tesis/c4.md`.

| Capa | Qué hace, en sencillo | Dónde |
|---|---|---|
| PWA ciudadana | Página que se instala en el celular. Permite reportar **sin cuenta** y consultar con un código. Si no hay señal, guarda el reporte y lo envía solo al volver la conexión | `app/pwa/` (`reportar.js`) |
| Panel por rol | Aplicación React: cada rol ve solo sus pestañas (cola, refugio, rescates, adopciones, indicadores, administración) | `panel/src/App.tsx` |
| Entrada HTTP | FastAPI arma la aplicación, valida datos y exige el rol correcto antes de entrar a cada ruta | `app/api/main.py` (`crear_app`), `app/api/rutas_*.py`, `app/api/seguridad.py` |
| Protecciones transversales | Cabeceras de seguridad y CSP estricta, tope del tamaño de las peticiones, bitácora de cada cambio | `app/api/middlewares.py` |
| Servicios (reglas de negocio) | Aquí viven RN-01 a RN-16: validar el reporte, confirmar, ofrecer y escalar rescates, cupos, adopción | `app/reportes/`, `app/rescates/`, `app/cupos/`, `app/adopciones/` |
| Triaje con IA | Reglas de urgencia + modelo TF-IDF. El modelo solo puede subir la prioridad; si duda, revisión humana; si falla o tarda más de 10 s, prioridad alta | `app/triaje/combinado.py`, `app/triaje/servicio.py` |
| Repositorios | Cada servicio habla con una interfaz (`Protocol`); hay versión en memoria (pruebas) y en PostgreSQL | `app/reportes/repositorio.py`, `repositorio_postgres.py` |
| Base de datos | PostgreSQL con migraciones Alembic; varias reglas también como `CHECK` o índices únicos | `app/bd/esquema.py`, `migraciones/versions/` |
| Avisos (outbox) | Confirmar guarda los avisos como pendientes en la misma transacción; otro proceso los envía con reintentos | `app/avisos/procesador.py` |
| Tareas de fondo | Envío de avisos, escalamientos y videos vencidos; solo consultan la base cuando hay trabajo | `app/tareas_de_fondo.py` |
| Video (opcional) | Un PC del equipo analiza la marcha del animal y devuelve una sugerencia y una vista previa | `servicios/video/`, `app/video/servicio.py` |

## 2. El recorrido de un reporte, de la PWA al rescate

1. **El ciudadano reporta** en `/app/`: descripción (≥ 20 caracteres) y GPS o dirección.
   `POST /reportes` → `ServicioReportes.registrar` valida RN-01 (`app/reportes/servicio.py`).
2. **La IA sugiere**: `ServicioTriaje.evaluar` combina reglas y modelo (`app/triaje/servicio.py`).
   Confianza < 0,6 con media o baja ⇒ «requiere revisión» (RN-02); error o > 10 s ⇒ alta y
   «sin clasificar» (RN-03).
3. **El ciudadano recibe un código** de 8 caracteres y puede adjuntar un video ≤ 60 s.
4. **El veterinario revisa la cola** (`GET /cola`, ordenada por gravedad) y confirma o ajusta con
   justificación (RN-06, RN-16): `ServicioConfirmacion` (`app/reportes/confirmacion.py`). La
   decisión y los avisos a los rescatistas se guardan **en la misma transacción**
   (`app/reportes/repositorio_postgres.py`, `confirmar`).
5. **Se avisa** por correo a los rescatistas libres de la comuna (`ServicioRescates.avisos_para`,
   `app/rescates/servicio.py`); el procesador del outbox lo envía.
6. **Un rescatista acepta**: los índices únicos parciales impiden que dos acepten el mismo caso o
   que uno tenga dos activos (RN-08, `app/bd/esquema.py`). Llega, y registra el resultado.
7. **Si nadie acepta** en 15 min (crítico) o 30 min (alto), se avisa al coordinador una sola vez y
   se ofrece a toda la ciudad (`revisar_escalamientos`, tabla `escalamientos`).
8. **El coordinador registra el ingreso** con el código: el cupo se toma con un `UPDATE`
   condicional; sin cupo, 409 (RN-04, `app/cupos/repositorio_postgres.py`).
9. **El ciudadano consulta** `GET /reportes/{codigo}/seguimiento`: solo pasos y fechas, nunca
   descripción, ubicación ni correos (RN-14, `app/reportes/seguimiento.py`).

## 3. Las 10 decisiones más importantes

| # | Decisión | Por qué | Evidencia |
|---|---|---|---|
| 1 | El ciudadano reporta sin cuenta | En una emergencia nadie se registra; el código reemplaza la cuenta | `rutas_reportes.py`, RN-14 |
| 2 | La IA sugiere, el veterinario decide | Un error de la IA no debe mandar un caso grave al final de la fila | RN-06, `confirmacion.py` |
| 3 | Falla segura | Si el clasificador falla, el caso sube a alta y lo mira una persona | RN-03, `triaje/servicio.py` |
| 4 | El modelo solo sube la prioridad | El modelo se entrenó con datos **sintéticos**; las reglas son el piso | `triaje/combinado.py`, `docs/tesis/triaje-ia.md` |
| 5 | Outbox para los avisos | Un correo caído no deshace una confirmación ni se pierde un aviso | `avisos/procesador.py`, DT-07 |
| 6 | Reglas críticas también en la base | Dos rescatistas a la vez, o dos ingresos con el último cupo, los resuelve PostgreSQL | índices `uq_rescates_*`, `ck_refugios_ocupados` |
| 7 | Repositorios intercambiables | Las pruebas corren en memoria y en PostgreSQL con el mismo contrato | `Protocol` en cada `repositorio.py`, `tests/conftest.py` |
| 8 | Seguridad desde el inicio | JWT con rol, Argon2id, datos personales cifrados (AES-256-GCM), límites de intentos | `seguridad/tokens.py`, `usuarios/contrasenas.py`, `seguridad/cifrado.py`, `usuarios/intentos.py` |
| 9 | El video se analiza fuera de Render | El plan gratis no tiene memoria ni GPU para MediaPipe; si el nodo está apagado, manda el texto | `servicios/video/`, `app/video/servicio.py` |
| 10 | Pruebas primero y CI exigente | Cada PR pasa Ruff, pytest con cobertura ≥ 90 %, accesibilidad, e2e y seguridad | `.github/workflows/ci.yml` |

## 4. El incidente de Neon (24 de noviembre)

- **Qué pasó:** Neon suspendió la base al agotar las 100 CU-h gratis del mes; desde entonces los
  despliegues de Render fallan porque `alembic upgrade head` no logra conectarse.
- **Causa:** la base nunca dormía. Neon solo se suspende tras 5 minutos sin consultas, y había
  consultas cada 15 s (avisos) y cada 60 s (escalamientos y videos), el sondeo de GitHub cada
  30 min y el nodo de video cada 15 s. A 0,25 CU todo el mes son unas 180 CU-h (estimado en `docs/aprende/despliegue.md`).
- **Arreglo:** el sondeo se apagó y ya no toca la base (#387); un interruptor
  `PATITAS_TAREAS_DE_FONDO` (#389); las tareas solo consultan cuando hay trabajo (#391, #392);
  el nodo espera hasta 5 min y la API le responde sin consultar la base (#393); un flujo para
  restaurar el respaldo en una base nueva (#395). Cuentas en `docs/aprende/despliegue.md`.
- **Lo que aprendí:** en un servicio «serverless» el costo depende de **cuántas veces** se
  despierta, no de cuánto trabajo hay; un `while True: sleep(15)` es invisible en local y caro en
  la nube. Hay que medir el consumo en reposo, no solo el rendimiento con carga, y tener un
  respaldo probado antes de necesitarlo.

## 5. Preguntas probables del jurado

| # | Pregunta | Respuesta corta | Dónde se ve |
|---|---|---|---|
| 1 | ¿Qué pasa si la IA se equivoca? | Solo sugiere; el veterinario confirma o ajusta con justificación, que queda registrada | `app/reportes/confirmacion.py`, tabla `decisiones_triaje` |
| 2 | ¿Y si la IA no responde? | A los 10 s se usa la falla segura: alta y «sin clasificar» | `app/triaje/servicio.py` (`TIEMPO_MAX_CLASIFICACION_S`) |
| 3 | ¿Con qué datos se entrenó el modelo? | Con datos sintéticos; por eso solo puede subir la prioridad y se documenta como no validado con datos reales | `scripts/ia/`, `docs/tesis/triaje-ia.md`, `DEUDA_TECNICA.md` (DT-04) |
| 4 | ¿Cómo evitan que dos rescatistas tomen el mismo caso? | Índices únicos parciales en `rescates`: el segundo `INSERT` falla | `app/bd/esquema.py` (`uq_rescates_reporte_vigente`) |
| 5 | ¿Cómo evitan pasarse del cupo con dos ingresos a la vez? | `UPDATE` condicional + `CHECK ocupados BETWEEN 0 AND capacidad` | `app/cupos/repositorio_postgres.py`, `ck_refugios_ocupados` |
| 6 | ¿Qué ve el ciudadano de su caso? | Solo el código, los pasos y sus fechas | `app/reportes/seguimiento.py`, RN-14 |
| 7 | ¿Cómo protegen los datos personales? | Contacto y perfil cifrados con AES-256-GCM; contraseñas con Argon2id; nunca en logs | `app/seguridad/cifrado.py`, `app/usuarios/contrasenas.py` |
| 8 | ¿Cómo se autentica el personal? | Token JWT con el rol; cada ruta exige el suyo | `app/seguridad/tokens.py`, `app/api/seguridad.py` (`exigir_rol`) |
| 9 | ¿Qué pasa si alguien prueba contraseñas? | 5 fallos por correo o 20 por IP en 15 min ⇒ 429 con `Retry-After` | `app/usuarios/intentos.py`, `app/config.py` |
| 10 | ¿Y si llegan cientos de reportes falsos? | 20 reportes por IP cada 15 min; descripción con sentido; descarte con justificación | `app/config.py` (`REPORTES_MAXIMOS_POR_IP`), `app/reportes/descripcion.py`, `descarte.py` |
| 11 | ¿Cómo saben si se envió un aviso? | Cada aviso tiene estado (pendiente, enviado, fallido) y el panel lo muestra; nunca se dice «enviado» si no lo está | `app/avisos/`, `GET /reportes/{codigo}/avisos` |
| 12 | ¿Qué pasa si nadie acepta un rescate? | A los 15/30 min se avisa al coordinador una vez y se ofrece a toda la ciudad | `app/rescates/servicio.py`, `app/config.py` (`ESCALAMIENTO_MINUTOS`) |
| 13 | ¿Funciona sin internet? | La PWA guarda el reporte y lo envía al volver la señal, sin duplicarlo (clave de idempotencia) | `app/pwa/reportar.js`, columna `clave_idempotencia` |
| 14 | ¿Cómo detectan reportes repetidos? | Avisan «posible duplicado» si hay otro a menos de 200 m y 2 horas; decide el veterinario | `app/reportes/duplicados.py` |
| 15 | ¿Quién puede cambiar o borrar la bitácora? | Nadie: un disparador rechaza `UPDATE` y `DELETE` | `migraciones/versions/0020_bitacora.py` |
| 16 | ¿Cómo se prueba? | pytest (memoria y PostgreSQL), Vitest, Playwright e2e con regresión visual, axe/Lighthouse, Bandit, Semgrep; cobertura mínima 90 % | `.github/workflows/ci.yml`, `tests/`, `e2e/` |
| 17 | ¿Es accesible? | WCAG 2.2 AA medido con axe-core en cada pantalla, claro y oscuro, en cada PR | `scripts/accesibilidad/revisar.mjs`, `docs/tesis/guia-estilo.md` |
| 18 | ¿Qué pasa si se pierde la base? | Respaldo diario cifrado, probado restaurándolo, y un flujo para restaurarlo en una base nueva | `.github/workflows/respaldo.yml`, `restaurar-a-neon-nuevo.yml`, `docs/aprende/respaldo.md` |
| 19 | ¿Por qué se cayó producción? | Las tareas de fondo no dejaban dormir a Neon (ver la sección 4) | `PLAN_CIERRE.md` §7, `docs/aprende/despliegue.md` |
| 20 | ¿Qué deuda técnica queda? | Validar el modelo con datos reales, entre otras; está escrita y priorizada | `DEUDA_TECNICA.md`, `PLAN_CIERRE.md` §5 |

## 6. Antes de entrar

- Abrir `docs/arquitectura.svg`, `docs/aprende/guion-demo.md` y este archivo.
- Tener el sistema local corriendo (`scripts/dev/arrancar_local.ps1`) por si producción tarda en
  despertar.
- Saber decir en una frase cada regla RN de `CLAUDE.md`.
