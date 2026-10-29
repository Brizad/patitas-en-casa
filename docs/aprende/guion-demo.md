# Guion de la demostración (10 minutos)

Recorrido para mostrarle al profesor el sistema completo en
https://patitas-en-casa-pnnk.onrender.com, con los datos de demostración.

## Antes de empezar (5 minutos antes, no durante)

1. En Render deben existir `PATITAS_DEMO_ACTIVA=true` y `PATITAS_DEMO_CONTRASENA` (ver
   `avance.md`, «Cómo crear las variables en Render»). Todas las cuentas de demostración
   usan esa contraseña.
2. **Despierta el servicio:** abre https://patitas-en-casa-pnnk.onrender.com/app/ y espera a
   que cargue (el plan gratis se duerme; la primera vez tarda 30 a 60 s).
3. Abre dos pestañas: la **PWA** (`/app/`) en modo celular (en Chrome: F12 → ícono del
   teléfono) y el **panel** (`/panel/`) en tamaño normal.
4. Ten a mano el código de un reporte para mostrar el seguimiento (el que crees en el paso 1).

| Cuenta | Correo |
|--------|--------|
| Veterinaria | `veterinaria@demo.patitas.co` |
| Rescatista | `rescatista@demo.patitas.co` |
| Coordinador | `coordinador@demo.patitas.co` |
| Adoptante | `adoptante@demo.patitas.co` |
| Alcaldía | `alcaldia@demo.patitas.co` |
| Administrador | `admin@demo.patitas.co` |

El panel guarda la sesión solo en memoria: para cambiar de cuenta pulsa **Salir**.

## 1. El ciudadano reporta (1 min 30 s) · PWA, sin cuenta

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

## 2. La IA sugiere la prioridad (1 min) · panel como **veterinaria**

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

## 3. El veterinario confirma (1 min)

**Qué hacer.** Pulsa **Confirmar crítica**. Muestra el mensaje: «aviso pendiente de envío».
Abre otro reporte y pulsa «Ajustar prioridad…»: intenta escribir «..........» como
justificación y muestra que la rechaza.

**Qué explicar.**
- La IA sugiere y la persona decide (RN-16). Cambiar la prioridad exige una justificación con
  palabras (RN-16 + D-07) y queda en la bitácora.
- El aviso a los rescatistas se guarda en la **misma transacción** que la decisión (outbox) y
  un procesador lo envía con reintentos: la pantalla nunca dice «se avisó» si no es cierto.
- Todo se hace también con el teclado: el primer Tab ofrece «Saltar a la cola» (D-08).

## 4. El rescatista acepta (1 min) · panel como **rescatista**

**Qué hacer.** Sal y entra con el rescatista. Está «Disponible» para toda la ciudad. En
**Ofertas de rescate** aparece el caso con su comuna. Pulsa **Aceptar rescate**, luego
**Llegué al sitio** y registra el resultado **Trasladado al refugio**.

**Qué explicar.**
- Solo ve casos confirmados críticos o altos de su zona; la dirección exacta solo aparece
  después de aceptar (privacidad).
- Un rescate tiene un solo rescatista y un rescatista un solo rescate activo (RN-08): lo
  garantizan índices únicos parciales en PostgreSQL, aunque dos acepten en el mismo segundo.
- Si nadie acepta en 15 min (crítico) o 30 min (alto), se avisa al coordinador (RF-23).

## 5. Ingreso al refugio (1 min) · panel como **coordinador**

**Qué hacer.** Entra con el coordinador. En **Refugio** registra el ingreso del perro
(nombre, especie, estado de salud). Muestra la barra de ocupación y la lista de animales con
su ficha clínica e historial.

**Qué explicar.**
- El cupo se toma con un `UPDATE` condicional: dos ingresos simultáneos no pueden pasar la
  capacidad; sin cupo responde 409 (RN-04). Al 90 % se alerta a los coordinadores de ese
  refugio (RF-07).
- El historial clínico solo crece: nada se edita ni se borra (RF-24).

## 6. Adopción con recomendación de la IA (2 min) · **adoptante** y **coordinador**

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

## 7. Indicadores (1 min) · **coordinador** o **Alcaldía**

**Qué hacer.** Abre **Indicadores**. Muestra los tiempos por prioridad, el acuerdo del
veterinario con el modelo y la recomendación por tipo de hogar. Pulsa **Exportar CSV**. Si
quieres, entra con la Alcaldía para mostrar que solo ve esta pantalla.

**Qué explicar.**
- Son conteos y tiempos, sin datos personales; la exportación quita descripción, dirección,
  GPS, hora y código (RF-31).
- El «acuerdo por versión del modelo» dice si la IA está ayudando: si el veterinario cambia
  mucho lo que sugiere, esa versión no sirve.
- Con el administrador se ve la **bitácora inmutable** (RF-32): la base rechaza editarla.

## Cierre (30 s)

«Todo esto corre en Render gratis desde un solo contenedor Docker; cada cambio pasó por un PR
con CI (gitleaks, Ruff, más de 600 pruebas con PostgreSQL real y 97 % de cobertura). Lo que
no cabe en el plan gratis —el análisis de video y la disponibilidad del 99 %— está
documentado con su plan en `trazabilidad.md`.»

## Si algo falla en vivo

- **La página no carga:** el servicio está despertando; espera 60 s y recarga.
- **«Correo o contraseña incorrectos»:** revisa `PATITAS_DEMO_CONTRASENA` en Render.
- **No hay ofertas para el rescatista:** confirma primero un reporte crítico o alto.
- **El ingreso responde «sin cupos»:** registra un egreso en la ficha de otro animal.
