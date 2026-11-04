# Estado del proyecto Patitas en Casa (para retomar en cualquier sesión)

Lee primero `CLAUDE.md`, `docs/aprende/avance.md` y `git log --oneline -20`.
Producción: https://patitas-en-casa-pnnk.onrender.com (Render + Neon PostgreSQL 18 + Mailjet).
El repositorio es **privado**: no hay `--auto`; unir solo con `gh pr checks` en verde y luego `gh pr merge --squash`.

## Hecho y verificado por Brayan (nov. 2026)
- 32/32 RF; v1.1.0 y v1.2.0 publicadas.
- Respaldo diario de Neon: secretos creados y flujo en verde (RNF-15).
- Correos reales por Mailjet: llegan al ciudadano al confirmar, al ser rescatado y al ingresar al refugio.
- UptimeRobot vigila la página cada 5 min (no se duerme); sondeo de GitHub cada 30 min.
- PWA: grabar video con la cámara o elegir de la galería (≤ 60 s, ≤ 50 MB).
- Historial del veterinario (#218), «Mis rescates» del rescatista (#220) y hora de llegada (#222).
- Póster de Ingeniería de Software II terminado.

## Pendiente de código
1. **Vista previa del video para el veterinario** (#215 y #216): el análisis funciona, pero el
   reproductor no aparece. El nodo en WSL ya tiene el código nuevo y ffmpeg. Falta revisar en la
   ventana de Ubuntu si `POST /video/trabajos/{id}/vista` responde 200 y si `tiene_vista` llega en
   true. Nota: el repo es privado, así que el nodo se actualiza copiando desde Windows:
   `cp -r /mnt/c/Users/braya/Documents/Proyectos/patitas-en-casa/servicios/video/. ~/patitas/servicios/video/`
2. Confirmar que se unieron los PR pedidos el 3-nov: evidencias nunca vacías en crítica o alta
   (RNF-09), rechazo de descripciones sin sentido (RN-01) y acciones de GitHub en Node 24.

## Pendiente de Brayan (no es código)
- Piloto con 10 personas (RNF-06): guía en `docs/aprende/piloto.md`; luego correr
  `scripts/operacion/resultados_piloto.py` y actualizar trazabilidad y póster.
- Antes de la sustentación: descartar en el panel los reportes de prueba sin sentido.
- Agregar al profesor como colaborador del repositorio.
