# Avance del plan

## Fase 0 · Preparación

- Integrado el incremento 3 (bundle, #63, #64): avisos con reintento, panel React del
  veterinario, Docker y `render.yaml` en `main`.
- Guía de estudio iniciada: `00-mapa.md`.
- **Render**: el Blueprint aún no está creado. Crearlo lo hace Brayan (es crear cuenta y
  aceptar términos): en Render, *New → Blueprint →* este repositorio. Después, cada merge a
  `main` se despliega solo. URL: pendiente.

## Fase 1 · Pantallas por rol (#67)

- PR apilados, en orden: #66 (docs) → #68 (administrador inicial) → #69 (cuentas) → #70
  (refugios) → #71 (panel rescatista) → #72 (panel refugio) → #73 (panel administrador) →
  guía de la fase.
- Probado en el navegador contra una API en memoria con cuentas de demostración.
- Para Render: agregar `PATITAS_ADMIN_CORREO` y `PATITAS_ADMIN_CONTRASENA` en *Environment*.
- Falta: que ingresos y ocupación usen el refugio del coordinador (fase 2).
- Guía: `fase-1-pantallas-por-rol.md`.

## Fase 2 · Refugio completo (#75)

- PR apilados, en orden: #76 (D-06, D-07) → #77 (versión del modelo) → #78 (descartar) →
  #79 (duplicados) → #80 (cupos por refugio) → #81 (ficha clínica) → #82 (egresos + panel de
  la cola) → #83 (panel de fichas) → guía de la fase.
- Probado en el navegador: descartar un duplicado y agregar una nota a la ficha.
- Falta: alerta de cupo por correo a los coordinadores **del refugio** (hoy va a la lista
  `PATITAS_CORREOS_COORDINADORES`); exportar la ficha queda para la fase 5.
- Guía: `fase-2-refugio-completo.md`.
