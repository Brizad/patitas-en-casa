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

## Fase 3 · Adopción (#85)

- PR apilados, en orden: #86 (adoptante y perfil) → #87 (publicar) → #88 (solicitar) → #89
  (decidir, RN-05, RN-11, seguimientos) → #90 (registrar seguimientos) → #91 (PDF) → #92
  (panel del adoptante) → #93 (panel del coordinador) → guía de la fase.
- Probado en el navegador de punta a punta: publicar → perfil → solicitar → aprobar →
  seguimientos programados. El PDF se abrió y se ve bien.
- Falta: devolución de un animal adoptado (RN-13: hoy el compromiso la pide, pero el sistema
  no la registra); límite de registros por IP en `POST /adoptantes` (anotado en
  `DEUDA_TECNICA.md` como DT-09).
- Guía: `fase-3-adopcion.md`.

## Fase 4 · IA (#95)

- PR apilados, en orden: #96 (clasificador entrenado) → #97 (compatibilidad) → #98
  (jornada, húngaro) → #99 (video: puerto y RN-07) → #100 (panel) → guía de la fase.
- El modelo de triaje se entrenó con datos sintéticos: sus métricas no son clínicas.
- No construido: análisis de video con MediaPipe (DT-10, con plan en `DEUDA_TECNICA.md`).
- Guía: `fase-4-ia.md`.

## Fase 5 · Cierre (#102)

- PR apilados, en orden: #103 (bitácora) → #104 (indicadores) → #105 (exportar) → #106
  (panel) → versión 1.0.0 y esta guía.
- 568 pruebas en verde, cobertura 98 %; vitest 21; build del panel sin errores.
- Guía: `fase-5-cierre.md`.

## Resumen para Brayan

**Qué quedó:** todo el plan, en PR pequeños y apilados (#66 a #107), cada uno con su CI en
verde. Ninguno está integrado a `main`: la regla 2 de `CLAUDE.md` pide tu revisión (P-01).

**Cómo integrarlos:** en orden, del más bajo al más alto. Cada PR apunta a la rama del
anterior; al integrar uno con *squash*, GitHub cambia la base del siguiente a `main`. Si un
PR muestra conflictos, pídeme «rebasa la cadena sobre main». Al terminar, crea la etiqueta
`v1.0.0` sobre `main`.

**Render:** crear el Blueprint (*New → Blueprint →* este repositorio) es tuyo (cuenta y
términos). Luego agrega en *Environment* `PATITAS_ADMIN_CORREO` y
`PATITAS_ADMIN_CONTRASENA`. Cada merge a `main` se despliega solo. **URL: pendiente.**

**Qué falta o quedó como deuda:**
- DT-04 (en parte): validar el modelo de triaje con reportes reales.
- DT-09: limitar por IP el registro público de adoptantes.
- DT-10: análisis de video con MediaPipe (no cabe en Render gratis; plan escrito).
- DT-07 y DT-08 (del incremento 3) siguen abiertas.
- RN-13 (devolución de un animal adoptado) solo está en el texto del compromiso.
- Revisa `preguntas-para-brayan.md`: P-01 a P-06.
