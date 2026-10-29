# Preguntas para Brayan

Decisiones que el asistente tomó solo para no detenerse (lo más simple y reversible).
Cada una dice qué se eligió y cómo cambiarla.

| # | Pregunta | Qué se eligió | Cómo cambiarlo |
|---|----------|---------------|----------------|
| P-01 | El plan dejó sin marcar «A o B» para los merges. **Resuelta el 29-10-2026:** Brayan autorizó integrar en el chat (un PR #108 y luego un PR por cambio con CI en verde). Falta que **tú** actualices la regla 2 de `CLAUDE.md`: el control de seguridad no deja que el asistente cambie sus propios permisos. Texto sugerido al final de esta tabla. | **B**: los PR quedan abiertos para que Brayan los apruebe, porque la regla 2 vigente de `CLAUDE.md` (II-02) pide su comentario de revisión antes de integrar, y el asistente no debe cambiar sus propias reglas de permiso. Solo se integró el incremento 3 (#64), que las instrucciones del bundle ya autorizaban. | Si eliges A, cambia tú la regla 2 de `CLAUDE.md` y dilo en el chat. |
| P-02 | Los PR dependen unos de otros (el administrador necesita el rol, el panel necesita los endpoints…). | **PR apilados**: cada PR parte de la rama del anterior y apunta a ella; el primero apunta a `main`. El CI se ejecuta en PR hacia cualquier rama. Ver la lista en orden en `avance.md`. | Integra en el orden de `avance.md`. Al integrar uno con *squash*, GitHub cambia la base del siguiente a `main`; si muestra conflictos, pide «rebasa la cadena sobre main». |
| P-03 | Render publica desde `main`. | Mientras los PR no se integren, Render solo tiene el incremento 3. | Integrar los PR de cada fase. |
| P-04 | D-07: ¿lista de motivos o mínimo de letras para la justificación? (tu plan dice «exigir letras») | Además de los 10 caracteres de RN-16, **5 letras como mínimo** (`MIN_LETRAS_JUSTIFICACION` en `app/config.py`), en el servidor y en el panel. Acepta motivos reales y cortos («Sangra mucho») y rechaza «..........» o «1234567890». La restricción de la base sigue contando solo caracteres. | Cambiar el número en `app/config.py` y `panel/src/mensajes.ts`, o pasar a una lista de motivos. |
| P-05 | RN-05 («restricción dura») y RN-09 a RN-13 no están detalladas en el código ni en los documentos del repositorio. | RN-05 = niños, otros animales y patio (`app/adopciones/reglas.py`); RN-10 = perfil lleno y seguimiento aceptado; RN-11 = una adopción aprobada por animal; RN-12 = seguimientos 30/90/180; RN-13 = devolución, solo en el texto del compromiso. | Ajustar `reglas.py` y el servicio con la redacción exacta del ERS. |
| P-06 | ¿El adoptante usa el panel o la PWA? | El **panel** (`/panel/`), con su propio registro y una sola pantalla: es lo más simple y reutiliza el inicio de sesión. | Mover las pantallas del adoptante a la PWA ciudadana. |
| P-07 | ¿Respaldo diario de la base de producción (RNF-15)? | **No se integró.** Hay un flujo listo (copia diaria con `pg_dump`, cifrada con AES-256, con prueba de restauración, guardada 30 días en GitHub Actions), pero saca una copia de los datos reales fuera de Render y esa decisión es tuya. | Pídeme «integra el respaldo» y crea en GitHub los secretos `RENDER_DATABASE_URL` (External Database URL de Render) y `RESPALDO_CLAVE`. O usa los respaldos de un plan pagado de Render. |
| P-08 | ¿Correo real para los avisos (RF-05, RF-18)? | Sin SMTP los avisos quedan en el log y en la app. | Crea en Render `PATITAS_SMTP_HOST`, `PATITAS_SMTP_USUARIO`, `PATITAS_SMTP_CONTRASENA` y `PATITAS_SMTP_REMITENTE` (por ejemplo, Gmail con contraseña de aplicación). |
| P-09 | ¿Subir videos (RF-01) y analizarlos (RF-03)? | No cabe en el plan gratis (ver `trazabilidad.md`, notas 1 y 2). | Decide si se crea un almacenamiento de objetos y un worker; el plan está en DT-10. |
| P-10 | ¿Prueba con usuarios reales (RNF-06)? | Pendiente: necesita 10 personas y un cronómetro. | Usa `guion-demo.md` como tarea y registra el tiempo y el puntaje SUS. |
| P-12 | DT-09: ¿qué hacer cuando alguien se registra con un correo que ya tiene cuenta? | Se responde igual que a un registro nuevo y **no se avisa** al dueño (no hay SMTP en producción, P-08). | Con SMTP configurado, pídeme «avisar al dueño del correo»: se encola un aviso «alguien intentó registrarse con tu correo» con el mismo outbox de #63. |

**Texto sugerido para la regla 2 de `CLAUDE.md` (lo pegas tú):**

> 2. **Merges (autorizado por Brayan el 2026-10-29):** el asistente integra un PR
>    (`gh pr merge --squash`) cuando el CI está en verde y el diff no tiene `.env`, contraseñas
>    reales ni tokens, y después de cada merge comprueba que la app en Render siga funcionando.
>    Cada PR tiene 300 líneas cambiadas o menos (sin contar archivos generados). Nunca hace
>    push directo a `main`.
