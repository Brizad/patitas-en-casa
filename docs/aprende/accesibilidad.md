# Accesibilidad medida (RNF-11, #147)

RNF-11 pide WCAG 2.2 nivel AA: contraste suficiente, todo usable con teclado y con lector de
pantalla, y objetivos táctiles de 24 px o más. Antes solo se había revisado a mano (teclado y
tamaño de botones en la prueba de punta a punta, #122). Ahora se **mide** con dos
herramientas y la medición corre en el CI en cada PR.

## Cómo se mide

| Herramienta | Qué revisa | Dónde |
|---|---|---|
| **axe-core** 4.14 (Deque) | Reglas WCAG 2.0, 2.1 y 2.2 A y AA, más sus «buenas prácticas»: contraste, etiquetas de formularios, nombres de botones, encabezados, regiones, tamaño de los objetivos (2.5.8) | Cada pantalla pública y cada pestaña de los 6 roles con sesión, en modo **claro y oscuro** (el contraste cambia con el tema) y en un celular de **320 px** |
| **Lighthouse** 13.6 (Google) | Categoría «Accesibilidad» (usa axe por dentro y suma sus propias revisiones). Puntaje mínimo exigido: **100** | Página de inicio, PWA (reportar y consultar) e inicio de sesión del panel |
| Reflujo a 320 px | WCAG 1.4.10: sin desplazamiento horizontal en un celular angosto (axe no lo mide) | Pantallas públicas y los roles que trabajan desde el teléfono (rescatista y adoptante) |

El recorrido lo hace un navegador real (Chrome, o Edge en Windows) controlado por
`scripts/accesibilidad/revisar.mjs`. Entra con las cuentas de demostración de `app/demo.py`,
envía un reporte para revisar también las pantallas «código de seguimiento» y «estado del
reporte», y abre cada pestaña de cada rol. El servidor es `servidor_demo.py`: la API en
memoria con los datos de demostración; la contraseña de las cuentas es aleatoria en cada
corrida y nunca está en el código.

```bash
pip install -r requirements.txt && (cd panel && npm ci && npm run build)
cd scripts/accesibilidad && npm ci
export PATITAS_DEMO_CONTRASENA="$(openssl rand -hex 16)"
python servidor_demo.py 8765 &
node revisar.mjs            # en Windows con Edge: A11Y_CANAL=msedge y CHROME_PATH=ruta de msedge.exe
```

Deja el detalle en `scripts/accesibilidad/informe.json` (en el CI se guarda como artefacto
«informe-accesibilidad»).

## Qué salió y cómo se corrigió

Primera medición (29 de octubre de 2026), 47 revisiones:

| Falla | Herramienta | Dónde | Por qué importa | Corrección |
|---|---|---|---|---|
| `landmark-one-main` y `region`: la página no tiene región principal y hay contenido fuera de toda región | axe y Lighthouse (puntaje **96**) | Panel: inicio de sesión y registro de adoptante (claro, oscuro y celular) | Quien usa lector de pantalla salta a la región principal con una tecla; sin `<main>` tiene que recorrer todo | El formulario de inicio de sesión y el de registro quedaron dentro de `<main>` (`panel/src/App.tsx`) |
| `page-has-heading-one`: no hay título de nivel 1 | axe | Las 11 pestañas con sesión de los 6 roles, en claro y oscuro (22 revisiones) | El lector de pantalla anuncia el título 1 como «de qué trata la página»; sin él, la estructura empieza en el nivel 2 | El nombre de la barra («Patitas en Casa · Panel») pasó de `<b>` a `<h1>`, con el mismo tamaño (`.marca` en `panel/src/estilos.css`) |

La página de inicio, la PWA ciudadana y el contraste de todas las pantallas (en los dos
temas) no tuvieron fallas desde la primera medición.

## Resultado final

**49 revisiones, 0 fallas.** axe-core: 0 fallas en 45 revisiones (claro, oscuro y celular) y 0
elementos que axe dejara «por revisar a mano». Lighthouse: **100** en inicio, PWA · Reportar, PWA · Consultar y
panel · inicio de sesión. Reflujo a 320 px: sin desplazamiento horizontal.

El CI (`.github/workflows/ci.yml`, paso «Accesibilidad») falla si aparece cualquier falla de
axe, un puntaje de Lighthouse menor que 100 o desplazamiento horizontal a 320 px.

## Lo que las herramientas NO prueban

Las herramientas automáticas encuentran una parte de los problemas (Deque, autora de axe, estima que
encuentra alrededor de la mitad de los problemas reales; muchos criterios necesitan a una persona).
Lo que falta, dicho claro:

1. **Lector de pantalla real.** Escuchar el recorrido completo con NVDA (gratis, Windows) o
   TalkBack (Android): que los avisos `aria-live` se anuncien una sola vez y en buen momento,
   y que el orden de lectura tenga sentido. Lo puede hacer Brayan en 20 minutos con el guion
   de la demostración.
2. **Zoom al 200 % y texto agrandado** en el teléfono (1.4.4): se revisó el reflujo a 320 px,
   que es lo más exigente, pero no el texto agrandado del sistema operativo.
3. **Mensajes de error comprensibles** (3.3.3): las herramientas ven que el error existe y
   está asociado al campo, no si se entiende. Los textos se escribieron en español sencillo
   y se revisaron en la prueba de punta a punta.
4. **Teclado**: se revisó a mano en la prueba de punta a punta (#122: dos fallas corregidas);
   axe solo confirma que los elementos interactivos son alcanzables y tienen nombre.

Por eso RNF-11 queda **parcial** en `trazabilidad.md`: lo medible está en 100 %, falta la
prueba con lector de pantalla y con personas (RNF-06).

## Para la sustentación

- **«¿Cómo sabes que cumple WCAG?»** No basta con decirlo: se mide con axe-core y Lighthouse en
  cada PR, en los dos temas y en celular, y se explica qué no cubren las herramientas.
- **«¿Qué encontraron?»** Dos fallas de estructura en el panel (región principal y título
  de nivel 1); ninguna de contraste. Ver la tabla de arriba.
- **«¿Por qué en modo oscuro también?»** Porque los colores cambian: un texto que se lee
  bien sobre blanco puede no leerse sobre gris oscuro.
