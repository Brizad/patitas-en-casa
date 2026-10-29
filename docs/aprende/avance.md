# Avance del plan

## Fase 0 · Preparación

- Integrado el incremento 3 (bundle, #63, #64): avisos con reintento, panel React del
  veterinario, Docker y `render.yaml` en `main`.
- Guía de estudio iniciada: `00-mapa.md`.
- **Render**: el Blueprint aún no está creado. Crearlo lo hace Brayan (es crear cuenta y
  aceptar términos): en Render, *New → Blueprint →* este repositorio. Después, cada merge a
  `main` se despliega solo. **Hecho por Brayan: https://patitas-en-casa-pnnk.onrender.com**

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
`PATITAS_ADMIN_CONTRASENA`. Cada merge a `main` se despliega solo. **URL: https://patitas-en-casa-pnnk.onrender.com**

**Qué falta o quedó como deuda:**
- DT-04 (en parte): validar el modelo de triaje con reportes reales.
- DT-09: limitar por IP el registro público de adoptantes.
- DT-10: análisis de video con MediaPipe (no cabe en Render gratis; plan escrito).
- DT-07 y DT-08 (del incremento 3) siguen abiertas.
- RN-13 (devolución de un animal adoptado) solo está en el texto del compromiso.
- Revisa `preguntas-para-brayan.md`: P-01 a P-06.

## Integración y despliegue (29 de octubre de 2026)

- Por indicación de Brayan, la cadena de PR apilados se integró en **un solo PR (#108)**: se
  hizo merge de `main` en `trabajo/cierre`, los 5 conflictos se resolvieron con la versión
  de `trabajo/cierre` (el merge no cambió ningún archivo), 573 pruebas en verde con
  PostgreSQL y CI en verde. Los PR #69 a #107 se cerraron con «Integrado en el PR de
  trabajo/cierre».
- Render desplegó solo: la API responde versión 1.0.0, la PWA, el panel y el catálogo de
  adopción responden 200 (las migraciones `0010` a `0021` corrieron) y `/cola` sin sesión
  responde 401. URL: https://patitas-en-casa-pnnk.onrender.com

## Cómo crear las variables en Render (paso a paso)

Las contraseñas **no están en el código**: tú las escribes en Render y el sistema las lee al
arrancar. Hazlo así:

1. Entra a https://dashboard.render.com e inicia sesión.
2. En la lista, haz clic en el servicio web **patitas-en-casa** (no en la base de datos).
3. En el menú de la izquierda, haz clic en **Environment**.
4. Pulsa **Add Environment Variable** (o **Edit** si ya existe) y crea, una por una:

   | Nombre (Key) | Valor (Value) | Para qué sirve |
   |--------------|---------------|----------------|
   | `PATITAS_ADMIN_CORREO` | tu correo real, p. ej. `brayan@…` | Tu cuenta de administrador. |
   | `PATITAS_ADMIN_CONTRASENA` | una contraseña tuya de 12 caracteres o más | Contraseña de esa cuenta. |
   | `PATITAS_DEMO_ACTIVA` | `true` | Carga los datos de demostración una sola vez. |
   | `PATITAS_DEMO_CONTRASENA` | otra contraseña de 12 caracteres o más | La usan **todas** las cuentas de demostración. |

5. Pulsa **Save Changes**. Render reinicia el servicio solo (tarda unos minutos).
6. Abre https://patitas-en-casa-pnnk.onrender.com/panel/ y entra con cualquiera de estas cuentas y la contraseña que pusiste en
   `PATITAS_DEMO_CONTRASENA`:

   | Rol | Correo |
   |-----|--------|
   | Administrador | `admin@demo.patitas.co` |
   | Veterinaria | `veterinaria@demo.patitas.co` |
   | Coordinador | `coordinador@demo.patitas.co` |
   | Rescatista | `rescatista@demo.patitas.co` |
   | Adoptante | `adoptante@demo.patitas.co` |
   | Alcaldía | `alcaldia@demo.patitas.co` |

Qué hay que saber:

- Las cuentas de demostración son ficticias (el dominio `demo.patitas.co` no existe).
- Los datos se cargan **una sola vez**: si la cuenta `veterinaria@demo.patitas.co` ya existe,
  no se vuelve a cargar nada aunque Render reinicie. Para empezar de cero hay que borrar la
  base (o crear una nueva) en Render.
- Para no volver a cargarlos en una base nueva, cambia `PATITAS_DEMO_ACTIVA` a `false`.
- No uses la misma contraseña para tu cuenta de administrador y para la demostración: la de
  demostración la verá quien asista a la presentación.
- Si alguna variable falta o la contraseña es corta, la API arranca igual y en *Logs* aparece
  el motivo (nunca la contraseña).
