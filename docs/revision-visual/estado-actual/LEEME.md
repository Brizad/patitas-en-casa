# Estado actual del diseño (25-nov-2026, #406)

Capturas **sin cambios de diseño**, para decidir los siguientes con mockups. Tomadas con
`scripts/accesibilidad/estado_actual.mjs` sobre el sistema local (PostgreSQL temporal y datos de
demostración), con Edge, a página completa.

Nombre: `<ancho>-<tema>-<pantalla>.jpg`, con ancho 360 o 1366 px y tema claro u oscuro.

| Pantalla | Archivo | Quién |
|---|---|---|
| Portada | `portada` | Público |
| PWA · Reportar | `pwa-reportar` | Ciudadano |
| PWA · Consultar | `pwa-consultar` | Ciudadano |
| Cola de triaje | `veterinario-cola` | `veterinaria@demo.patitas.co` |
| Detalle de un reporte (el primero de la cola) | `veterinario-detalle` | `veterinaria@demo.patitas.co` |
| Inicio del coordinador (Refugio) | `coordinador-inicio` | `coordinador@demo.patitas.co` |
| Inicio del rescatista (Ofertas y rescate actual) | `rescatista-inicio` | `rescatista@demo.patitas.co` |
| Inicio del adoptante | `adoptante-inicio` | `adoptante@demo.patitas.co` |

Para repetirlas: `cd scripts\accesibilidad; npm ci`, y con el sistema local corriendo,
`$env:PATITAS_DEMO_CONTRASENA="<la de tu .env>"; $env:A11Y_CANAL="msedge"; node estado_actual.mjs`.
