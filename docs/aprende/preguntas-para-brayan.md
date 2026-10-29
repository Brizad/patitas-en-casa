# Preguntas para Brayan

Decisiones que el asistente tomó solo para no detenerse (lo más simple y reversible).
Cada una dice qué se eligió y cómo cambiarla.

| # | Pregunta | Qué se eligió | Cómo cambiarlo |
|---|----------|---------------|----------------|
| P-01 | El plan dejó sin marcar «A o B» para los merges. | **B**: los PR quedan abiertos para que Brayan los apruebe, porque la regla 2 vigente de `CLAUDE.md` (II-02) pide su comentario de revisión antes de integrar, y el asistente no debe cambiar sus propias reglas de permiso. Solo se integró el incremento 3 (#64), que las instrucciones del bundle ya autorizaban. | Si eliges A, cambia tú la regla 2 de `CLAUDE.md` y dilo en el chat. |
| P-02 | Los PR dependen unos de otros (el administrador necesita el rol, el panel necesita los endpoints…). | **PR apilados**: cada PR parte de la rama del anterior y apunta a ella; el primero apunta a `main`. El CI se ejecuta en PR hacia cualquier rama. Ver la lista en orden en `avance.md`. | Integra en el orden de `avance.md`. Al integrar uno con *squash*, GitHub cambia la base del siguiente a `main`; si muestra conflictos, pide «rebasa la cadena sobre main». |
| P-03 | Render publica desde `main`. | Mientras los PR no se integren, Render solo tiene el incremento 3. | Integrar los PR de cada fase. |
| P-04 | D-07: ¿lista de motivos o mínimo de letras para la justificación? (tu plan dice «exigir letras») | Además de los 10 caracteres de RN-16, **5 letras como mínimo** (`MIN_LETRAS_JUSTIFICACION` en `app/config.py`), en el servidor y en el panel. Acepta motivos reales y cortos («Sangra mucho») y rechaza «..........» o «1234567890». La restricción de la base sigue contando solo caracteres. | Cambiar el número en `app/config.py` y `panel/src/mensajes.ts`, o pasar a una lista de motivos. |
