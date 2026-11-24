# Guion del video demo (máximo 5 minutos)

Video corto para el jurado: el recorrido completo de un caso, del celular del ciudadano a la
adopción, y por qué se puede confiar en el sistema. Al final está el recorrido **en vivo** de
10 minutos (anexo), por si hay que mostrarlo de frente.

## Antes de grabar

1. **Grábalo en local** para no depender de que Render despierte: `scripts\dev\arrancar_local.ps1`
   (ver `desarrollo-local.md`). Si usas producción, abre `/app/` 2 minutos antes.
2. Base con los datos de demostración **recién cargados** (cola con 4 reportes, un crítico
   esperando rescatista, animales en el refugio y en adopción).
3. Dos ventanas lado a lado: la **PWA** en modo celular (Chrome o Edge: F12 → ícono del
   teléfono, 390 px) y el **panel** a 1366 px. Zoom del navegador al 110 %.
4. Ten escrito el texto del reporte para pegarlo:
   «Perro atropellado frente al parque Santander, no se levanta y sangra mucho».
5. Todas las cuentas usan la contraseña de `PATITAS_DEMO_CONTRASENA`. Para cambiar de cuenta,
   **Salir**.

## Escenas

| Tiempo | Pantalla | Cuenta |
|---|---|---|
| 0:00–0:20 | Portada `/` | ninguna |
| 0:20–1:05 | PWA: reportar, código y consultar | ninguna (ciudadano) |
| 1:05–1:55 | Cola de triaje y detalle; confirmar | `veterinaria@demo.patitas.co` |
| 1:55–2:35 | Ofertas, aceptar, llegué, resultado (celular) | `rescatista@demo.patitas.co` |
| 2:35–3:10 | Refugio: ingreso con el código y cupos | `coordinador@demo.patitas.co` |
| 3:10–3:45 | Recomendados para tu hogar y solicitud | `adoptante@demo.patitas.co` |
| 3:45–4:15 | Indicadores anonimizados | `alcaldia@demo.patitas.co` |
| 4:15–4:45 | Calidad: arquitectura y CI | (GitHub) |
| 4:45–5:00 | Cierre | — |

### 0:00 · Portada
**Mostrar:** la portada y sus tres botones. **Decir:** «Patitas en Casa ayuda a que un perro o
un gato herido en Cúcuta llegue rápido a quien lo puede atender. Lo vamos a seguir de principio
a fin.»

### 0:20 · El ciudadano reporta (PWA, sin cuenta)
**Hacer:** Reportar → pegar el texto → escribir «Barrio La Playa, calle 10» → comuna 2 →
**Enviar reporte** → aparece el código → pestaña **Consultar** con ese código.
**Decir:** «No pide cuenta: en una emergencia nadie se registra. Exige 20 caracteres y una
ubicación (RN-01). Sin señal, el reporte se guarda y sale solo después. Con el código, el
ciudadano ve los pasos y sus fechas, nunca la dirección ni datos de otras personas (RN-14).»

### 1:05 · La IA sugiere, el veterinario decide
**Hacer:** entrar como veterinaria → el reporte nuevo arriba como **Crítica** → abrirlo →
señalar «Sugerencia del sistema» y «En qué se basa» → **Confirmar crítica**.
**Decir:** «La IA combina reglas y un modelo de texto; el modelo solo puede subir la prioridad.
Si duda, el caso va a revisión humana (RN-02); si falla, sube a alta (RN-03). Decide la
veterinaria; cambiarla exige una justificación que queda registrada (RN-16). Al confirmar, los
avisos quedan pendientes en la misma operación y se envían aparte: nunca se pierde uno.»

### 1:55 · El rescatista acepta (celular)
**Hacer:** entrar como rescatista → **Disponible** → la oferta crítica → **Aceptar rescate** →
**Llegué al sitio** → resultado **Trasladado al refugio** → **Registrar resultado**.
**Decir:** «Solo ve casos críticos o altos de su zona, y la dirección después de aceptar. Un
rescate tiene un solo rescatista y cada rescatista uno activo: lo garantiza la base aunque dos
toquen a la vez (RN-08). Si nadie acepta en 15 minutos, se avisa al coordinador.»

### 2:35 · Ingreso al refugio
**Hacer:** entrar como coordinador → **Refugio** → nombre «Rayo», especie, estado de salud y el
**código del reporte** → **Registrar ingreso** → señalar la barra de ocupación.
**Decir:** «El cupo se toma en la base de forma atómica: sin cupo, no entra (RN-04), y al 90 %
se alerta. Con el código, el ciudadano sabe que su perro llegó.»

### 3:10 · Adopción
**Hacer:** entrar como adoptante → **Mi perfil** → **Recomendados para tu hogar** con el puntaje
y las razones → **Quiero adoptarlo**.
**Decir:** «La compatibilidad mira el hogar y el animal, no datos sensibles de la persona. Una
restricción dura, como niños en casa y un animal que no convive con niños, impide aprobar.»

### 3:45 · Indicadores para la Alcaldía
**Hacer:** entrar como alcaldía → indicadores → **Exportar PDF**.
**Decir:** «La Alcaldía solo ve cifras anonimizadas: sin nombres, direcciones, correos ni códigos.»

### 4:15 · Por qué se puede confiar
**Mostrar:** `docs/arquitectura.svg` y la pestaña *Actions* del repositorio con el CI en verde.
**Decir:** «Cada cambio entró por un Pull Request con pruebas primero: unitarias, de la API con
PostgreSQL, accesibilidad con axe en claro y oscuro, pruebas de punta a punta y escaneos de
seguridad. Las contraseñas van con Argon2id y los contactos cifrados.»

### 4:45 · Cierre
**Decir:** «Patitas en Casa: reportar en segundos, decidir con ayuda de la IA, rescatar sin
duplicar esfuerzos y adoptar con responsabilidad.»

## Si algo falla al grabar

- **La página no carga:** el servidor está despertando; espera y recarga, o graba en local.
- **«Correo o contraseña incorrectos»:** la contraseña es la de `PATITAS_DEMO_CONTRASENA`.
- **No hay ofertas para el rescatista:** confirma primero un reporte crítico o alto.
- **El ingreso dice «sin cupos»:** registra un egreso en la ficha de otro animal.

---

## Anexo: demostración en vivo (10 minutos)

Mismo recorrido con más detalle, para mostrarlo de frente al profesor.

### 1. El ciudadano reporta (1 min 30 s) · PWA, sin cuenta

**Qué hacer.** En la PWA escribe: «Perro atropellado frente al parque Santander, no se
levanta y sangra mucho». En ubicación pulsa «Usar mi GPS» o escribe una dirección; elige la
comuna 2 y pulsa **Enviar reporte**. Copia el código.

**Qué explicar.**
- No pide cuenta ni documento (RF-01): un ciudadano en la calle no se va a registrar.
- RN-01: exige 20 caracteres y una ubicación; el formulario lo valida y el servidor también.
- Sin señal el reporte se guarda en el teléfono y se envía solo al volver la conexión, sin
  duplicarse (RF-12, clave de idempotencia).
- El contacto es opcional, pide autorización (Ley 1581) y se guarda cifrado con AES-256.
- Pulsa «Ver estado»: solo pasos y fechas, nunca la descripción ni la dirección (RN-14).

### 1b. (Opcional) El video del animal (1 min) · PWA + trabajador local

**Antes:** el trabajador local debe estar corriendo (`servicios/video/README.md`) con el
`PATITAS_VIDEO_TOKEN` de Render. Ten listo un video corto de un perro caminando de lado.

**Qué hacer.** En el reporte del paso 1, elige el video en «Video del animal (opcional)»
antes de enviar. Muestra «Video listo: 12 s · 8 MB» y, tras enviar, «Video recibido, se está
analizando». En la terminal del trabajador aparece «trabajo N analizado en X s».

**Qué explicar.**
- MediaPipe Pose solo sirve para personas: se usa MediaPipe para encontrar al perro y
  DeepLabCut SuperAnimal-Quadruped para sus 39 puntos; con ellos se mide la marcha.
- Corre en una PC del equipo porque no cabe en Render gratis; la PC **pide** los videos y no
  abre puertos. El video se borra al terminar (RNF-08).
- Si el trabajador está apagado o el video no sirve, manda el texto (falla segura).
- En el paso 2, el detalle del reporte muestra «Análisis de video: listo», sus evidencias, la
  discrepancia con el texto (RF-19) y la tira de 3 cuadros.

### 2. La IA sugiere la prioridad (1 min) · panel como **veterinaria**

**Qué hacer.** Entra con la veterinaria. En la **Cola de triaje** aparece tu reporte arriba,
como **Crítica**. Ábrelo.

**Qué explicar.**
- La cola se ordena por gravedad: crítica, alta, «requiere revisión», media, baja (RF-04).
- La sugerencia viene de reglas validadas + un modelo TF-IDF; el modelo **solo puede subir**
  la prioridad, nunca bajarla. Fue entrenado con datos **sintéticos** (y se dice así).
- Las **evidencias** (al menos 3) explican el porqué (RNF-09) y se ve la versión del modelo
  (RF-20). Si dos reportes están a menos de 200 m y 2 h, la cola los marca como posible
  duplicado (RF-17).
- Con confianza baja nunca se asigna media o baja sola (RN-02); si el clasificador falla, el
  reporte sube a alta y va a revisión manual (RN-03).

### 3. El veterinario confirma (1 min)

**Qué hacer.** Pulsa **Confirmar crítica**. Muestra el mensaje: «aviso pendiente de envío».
Abre otro reporte y pulsa «Ajustar prioridad…»: intenta escribir «..........» como
justificación y muestra que la rechaza.

**Qué explicar.**
- La IA sugiere y la persona decide (RN-16). Cambiar la prioridad exige una justificación con
  palabras (RN-16 + D-07) y queda en la bitácora.
- El aviso a los rescatistas se guarda en la **misma transacción** que la decisión (outbox) y
  un procesador lo envía con reintentos: la pantalla nunca dice «se avisó» si no es cierto.
- Todo se hace también con el teclado: el primer Tab ofrece «Saltar a la cola» (D-08).

### 4. El rescatista acepta (1 min) · panel como **rescatista**

**Qué hacer.** Sal y entra con el rescatista. Está «Disponible» para toda la ciudad. En
**Ofertas de rescate** aparece el caso con su comuna. Pulsa **Aceptar rescate**, luego
**Llegué al sitio** y registra el resultado **Trasladado al refugio**.

**Qué explicar.**
- Solo ve casos confirmados críticos o altos de su zona; la dirección exacta solo aparece
  después de aceptar (privacidad).
- Un rescate tiene un solo rescatista y un rescatista un solo rescate activo (RN-08): lo
  garantizan índices únicos parciales en PostgreSQL, aunque dos acepten en el mismo segundo.
- Si nadie acepta en 15 min (crítico) o 30 min (alto), se avisa al coordinador (RF-23).

### 5. Ingreso al refugio (1 min) · panel como **coordinador**

**Qué hacer.** Entra con el coordinador. En **Refugio** registra el ingreso del perro
(nombre, especie, estado de salud). Muestra la barra de ocupación y la lista de animales con
su ficha clínica e historial.

**Qué explicar.**
- El cupo se toma con un `UPDATE` condicional: dos ingresos simultáneos no pueden pasar la
  capacidad; sin cupo responde 409 (RN-04). Al 90 % se alerta a los coordinadores de ese
  refugio (RF-07).
- El historial clínico solo crece: nada se edita ni se borra (RF-24).

### 6. Adopción con recomendación de la IA (2 min) · **adoptante** y **coordinador**

**Qué hacer.**
1. Entra con la adoptante. Muestra su perfil (vivienda, niños, horas solo…) y la lista
   **Recomendados para tu hogar**, con el puntaje y las 3 razones. Pulsa **Quiero adoptarlo**
   en Canela.
2. Entra con el coordinador → **Adopciones**: la solicitud trae la compatibilidad. Pulsa
   **Aprobar**. Muestra los tres seguimientos (30, 90 y 180 días).
3. (Si hay tiempo) Pulsa «Calcular propuesta» en **Jornada de adopción**.

**Qué explicar.**
- El perfil no pide edad, género, estrato ni ingresos: la compatibilidad solo mira el hogar y
  el animal (RNF-16). Una restricción dura (por ejemplo, el animal no convive con niños y hay
  niños) impide aprobar (RN-05).
- Aprobar es una sola transacción: rechaza las otras solicitudes del animal, da el egreso,
  libera el cupo y programa los seguimientos. Una sola adopción aprobada por animal (RN-11).
- La jornada usa el algoritmo húngaro para maximizar la compatibilidad total (RF-28).
- La adoptante puede descargar el compromiso en PDF para firmarlo (RF-29).

### 7. Indicadores (1 min) · **coordinador** o **Alcaldía**

**Qué hacer.** Abre **Indicadores**. Muestra los tiempos por prioridad, el acuerdo del
veterinario con el modelo y la recomendación por tipo de hogar. Pulsa **Exportar CSV**. Si
quieres, entra con la Alcaldía para mostrar que solo ve esta pantalla.

**Qué explicar.**
- Son conteos y tiempos, sin datos personales; la exportación quita descripción, dirección,
  GPS, hora y código (RF-31).
- El «acuerdo por versión del modelo» dice si la IA está ayudando: si el veterinario cambia
  mucho lo que sugiere, esa versión no sirve.
- Con el administrador se ve la **bitácora inmutable** (RF-32): la base rechaza editarla.

### Cierre (30 s)

«Todo esto corre en Render gratis desde un solo contenedor Docker; cada cambio pasó por un PR
con CI (gitleaks, Ruff, pytest con PostgreSQL real y cobertura mínima del 90 %). El análisis
de video corre en un trabajador local porque no cabe en el plan gratis; lo que sigue
pendiente —la disponibilidad del 99 % y validar los modelos con veterinarios— está en
`../tesis/trazabilidad.md`.»

### Si algo falla en vivo

- **La página no carga:** el servicio está despertando; espera 60 s y recarga.
- **«Correo o contraseña incorrectos»:** revisa `PATITAS_DEMO_CONTRASENA` en Render.
- **No hay ofertas para el rescatista:** confirma primero un reporte crítico o alto.
- **El ingreso responde «sin cupos»:** registra un egreso en la ficha de otro animal.
