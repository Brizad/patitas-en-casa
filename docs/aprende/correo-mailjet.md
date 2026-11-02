# Correo de avisos con Mailjet

**Por qué:** Render gratis bloquea los puertos SMTP (25, 465 y 587), así que con
`PATITAS_SMTP_HOST` los avisos nunca salían. Mailjet ofrece una API por HTTPS (puerto 443,
abierto) y el adaptador `NotificadorMailjet` (`app/notificaciones/mailjet.py`) la usa.

## Qué decide la app al arrancar

1. Si están `PATITAS_MAILJET_API_KEY` **y** `PATITAS_MAILJET_SECRET_KEY` → Mailjet
   (además exige `PATITAS_CORREO_REMITENTE`; si falta, la app no arranca y lo dice).
2. Si no, y hay `PATITAS_SMTP_HOST` → SMTP, como antes.
3. Si no, el aviso queda en el log, como antes.

El outbox y los reintentos (#63) no cambian: el aviso solo pasa a `enviado` cuando Mailjet
responde `success`. Un 400 o 422 es falla permanente (no se reintenta); 401, 403, 429 y 5xx se
reintentan. Que Mailjet acepte el mensaje no prueba que la persona lo haya leído.

## Qué hacer en Render (ya creaste las tres variables)

| Variable | Valor |
|----------|-------|
| `PATITAS_MAILJET_API_KEY` | *API Key* de Mailjet (Account → API Key Management) |
| `PATITAS_MAILJET_SECRET_KEY` | *Secret Key* de esa misma pantalla |
| `PATITAS_CORREO_REMITENTE` | Correo **validado** en Mailjet (Senders & domains) |

Mailjet solo envía desde un remitente validado: si no lo validaste, responde 401/403 y los
avisos quedan `pendiente` reintentando. Para los coordinadores también define
`PATITAS_CORREOS_COORDINADORES` (correos separados por comas).

## Cómo probar

Confirma un reporte crítico con un rescatista de correo real: el aviso debe aparecer como
`enviado` y llegar a su bandeja (revisa también el spam). En Mailjet → *Statistics* se ven los
envíos. Nunca pegues las claves en el chat, en issues ni en el repositorio.

Las pruebas (`tests/test_mailjet.py`) usan un servidor HTTP falso en tu propio computador:
no envían correos reales.
