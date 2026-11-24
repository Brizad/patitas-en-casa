# Revisión visual y de experiencia (24-nov-2026, #400)

**Cómo se hizo.** Sistema local completo (API + PostgreSQL 17 + panel compilado + PWA, con los
datos de demostración) y `scripts/accesibilidad/revision_visual.mjs` (Playwright, Edge): todas las
pantallas públicas y todas las pestañas de los seis roles del panel, a **360 y 1366 px**, en
**claro y oscuro**. 19 pantallas × 2 anchos × 2 temas = 76 capturas en `antes/`
(`<ancho>-<tema>-<pantalla>.jpg`). El ciudadano usa la PWA (`pwa-reportar`, `pwa-consultar`).

**Referencias.** `docs/tesis/guia-estilo.md`. La guía cita `DESIGN.md` como referencia editorial,
pero **ese archivo no está en el repositorio**: se siguió la guía, que dice que manda el código.
Lo que la guía decide a propósito no se cuenta como hallazgo (por ejemplo, la primera cifra clave
invertida en Indicadores y Modo piloto).

**Lo que ya está bien.** Sin desbordes a 360 px; las tablas (cuentas, bitácora, historial, mis
rescates) ya se vuelven tarjetas en el celular; el modo oscuro es coherente en todas las pantallas;
la PWA, el inicio de sesión y la portada son claros y consistentes.

## Hallazgos, ordenados por impacto

| # | Pantalla | Qué se ve | Por qué importa | Arreglo |
|---|---|---|---|---|
| 1 | Cola, Historial, Mis rescates, Refugio, Indicadores | Mientras llegan los datos no se ve **nada**: la tarjeta queda vacía (o dice «no hay…» al fallar) y solo «Actualizar» se desactiva. Con Render despertando son hasta 60 s | Parece que no hay datos o que se colgó | Indicador «Cargando…» con `role="status"` en cada lista |
| 2 | Todo el panel a 1366 px | La cabecera y las pestañas van de borde a borde a la izquierda, y el contenido es una columna de ~460 px centrada (en la cola, dos columnas pegadas a la izquierda con medio pantallazo vacío) | Desalineado; desperdicia el ancho justo donde el personal trabaja | Un mismo ancho máximo y margen para cabecera, pestañas y contenido |
| 3 | Cola (360 px) | Al final de la lista queda una tarjeta punteada «Elige un reporte de la cola.» | En el celular no hay nada al lado que elegir: es ruido al final | Ocultarla en el celular; en escritorio, decir qué pasa al elegir |
| 4 | Varias | Títulos y ayudas con códigos internos: «Modo piloto (RNF-06)», «(RF-31)», «(RF-32)», «(RF-20)», «(RNF-16)», «(RF-10, RN-13)», «(RF-28)», «(RN-04)», «(RF-17)», «(RN-06)», «(RN-07, RF-19)» y «Solo coordinación registra ingresos (pantalla P-06)» | Jerga del documento de requisitos: al veterinario o a la Alcaldía no les dice nada | Quitar los códigos del texto visible (siguen en los comentarios del código) |
| 5 | Adoptante, Adopciones, Cola, Historial, Mis rescates | Estados vacíos dispares: «Solicitudes pendientes» trae título y qué esperar; «Aún no has hecho solicitudes», «No hay adopciones aprobadas», «No hay seguimientos programados» son una sola línea sin siguiente paso | El vacío no orienta: no dice qué hacer | Todos con frase principal + qué hacer o cuándo se llenará |
| 6 | Refugio, Modo piloto vs. Cola, Historial, Mis rescates | «Actualizar» a veces a la derecha del título y a veces debajo, como una línea aparte | Botones inconsistentes entre pestañas del mismo rol | Cabecera de tarjeta igual en todas: título a la izquierda, acción a la derecha |
| 7 | Historial y Mis rescates (360 px) | En cada tarjeta el código es una fila más («Código ··· VZSTZXUN»); todas las filas pesan igual | Cuesta separar una tarjeta de la siguiente | El primer dato de la fila encabeza la tarjeta |
| 8 | Indicadores (Seguimientos de adopción) | Con valor 0 se dibuja una rayita «▏0» | Parece una barra rota | Una barra en 0 no se dibuja |
| 9 | Rescatista · Mi disponibilidad | Leyenda «Zona: Toda la ciudad (sin marcar = toda la ciudad)», repetida y montada sobre el borde | Confusa y desalineada | «Zona: toda la ciudad» y debajo una ayuda corta |
| 10 | Modo piloto | «Descargar CSV» deshabilitado sin explicación | No se sabe cuándo se podrá usar | Ayuda «Se habilita cuando alguien termine la prueba» |
| 11 | Cabecera del panel (360 px) | «Dra. Ana Pérez (demo) · ícono» y debajo «Veterinario»: el punto y el ícono quedan colgando | Detalle menor | Pendiente |
| 12 | Refugio, Perfil del adoptante (360 px) | Casillas separadas ~70 px entre sí | Formulario largo; el objetivo táctil ya mide 44 px | Pendiente |
| 13 | Indicadores · Bitácora | Las últimas 50 entradas son casi todas «inicio de sesión» | Tapa los cambios que importan | Pendiente (filtro por acción) |
| 14 | Foto para el catálogo | El botón nativo dice «No se e… archivo» (texto cortado del navegador) | Detalle menor del control nativo | Pendiente |

## Qué se corrigió

| Hallazgos | PR |
|---|---|
| 1 (cargas con indicador), 5 (estados vacíos), 6 («Actualizar» a la derecha) | #403 |
| 2 (alineación en escritorio), 3 (cola en el celular), 4 (sin códigos internos), 7 (tarjetas con encabezado), 8 (barras en 0), 9 (zona del rescatista), 10 (CSV del piloto) | #405 |
| 11 a 14 | pendientes |

Las capturas de después están en `despues/`, con los mismos nombres (tomadas con la rama de #405).
axe-core y Lighthouse siguen sin fallas: los revisa el job `build-lint-test` del CI en cada PR.

## Cómo repetirla

```powershell
# con el sistema local corriendo (docs/aprende/desarrollo-local.md)
cd scripts\accesibilidad; npm ci
$env:PATITAS_DEMO_CONTRASENA = "<la de tu .env>"; $env:A11Y_CANAL = "msedge"
node revision_visual.mjs despues http://127.0.0.1:8000
```
