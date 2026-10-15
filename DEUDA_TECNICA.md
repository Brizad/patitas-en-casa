# Registro de deuda técnica

| ID | Atajo tomado | Cuadrante (Fowler) | Plan de pago |
|----|--------------|--------------------|--------------|
| DT-01 | Repositorio de reportes en memoria en lugar de PostgreSQL | Deliberada y prudente | **Pagada** en el incremento 2 (#10: #23, #25, #27, #29): `RepositorioPostgres` detrás de `RepositorioReportes`, migraciones de Alembic y CI con PostgreSQL. |
| DT-02 | Rol del usuario enviado en el encabezado `X-Rol`, sin autenticación real | Deliberada y prudente (solo en entorno local) | **Pagada** en el incremento 2 (#11: #35, #37, #40): cuentas con Argon2id, inicio de sesión OAuth2 con JWT y endpoints del personal protegidos; `X-Rol` eliminado. |
| DT-03 | Notificaciones impresas en consola | Deliberada y prudente | **Pagada** en el incremento 2 (#12): `NotificadorCorreo` (SMTP con STARTTLS) detrás de `Notificador`; sin SMTP configurado, `NotificadorRegistro` escribe la alerta en el log. Web Push queda para HU-06 en el incremento 3. |
| DT-04 | Clasificador de triaje por reglas en lugar del modelo Transformer | Deliberada y prudente | Incremento 2: entrenar y comparar el modelo con el conjunto de validación (RNF-03, recall ≥ 0,95). |
| DT-05 | Cupos del refugio y animales en memoria; el candado de BUG-04 solo protege un proceso | Deliberada y prudente (encontrada al pagar DT-01) | **Pagada** en el incremento 2 (#30): tablas `refugios` y `animales`, cupo ocupado con un `UPDATE` condicional en PostgreSQL y prueba de concurrencia contra la base (RN-04). |
| DT-06 | `POST /auth/token` no limita los intentos fallidos (fuerza bruta); hoy lo mitigan Argon2id, el mínimo de 12 caracteres y el mensaje de error uniforme | Deliberada y prudente (registrada al pagar DT-02) | **Pagada** en el incremento 2 (#41): tabla `intentos_fallidos` (migración `0004`) y `LimiteIntentos`; 5 fallos por correo o 20 por IP en 15 minutos responden 429 con `Retry-After`, sin mirar la contraseña mientras dura el bloqueo. Ya no bloquea el release 1.0.0. |
