"""Parámetros de negocio del MVP (línea base de requisitos v1.1)."""

# RNF-03: por debajo de esta confianza el reporte exige revisión humana.
UMBRAL_CONFIANZA = 0.6

# P-16 (#285): cuántos niveles puede subir el modelo de texto sobre las reglas. None = sin
# tope, como hasta hoy («el modelo solo sube»). Con 1, un texto que las reglas ven «media» llega
# a «alta» como mucho. Lo decide Brayan: frena falsas alarmas, pero puede bajar el recall de
# «crítica» si las reglas no conocen la palabra (ver docs/aprende/errores-ia-texto.md).
MODELO_SUBE_MAX_NIVELES: int | None = None

# RF-07: porcentaje de ocupación a partir del cual se alerta al coordinador.
ALERTA_OCUPACION = 0.90  # línea base v1.1 (RF-07)

# RF-01: límites del video adjunto al reporte.
VIDEO_MAX_SEGUNDOS = 60
VIDEO_MAX_MB = 50

# RN-16: ajustar la prioridad sugerida exige justificación (prototipo, P-04 "Ajustar").
MIN_CARACTERES_JUSTIFICACION = 10
# D-07 (#75): además, un mínimo de letras; «..........» o «1234567890» no explican nada.
MIN_LETRAS_JUSTIFICACION = 5

# DT-06: intentos fallidos de inicio de sesión permitidos dentro de la ventana. Por IP el
# máximo es mayor porque el personal de un refugio suele compartir la misma IP pública.
INTENTOS_MAXIMOS = 5
INTENTOS_MAXIMOS_POR_IP = 20
VENTANA_INTENTOS_MINUTOS = 15
# DT-09 (#149): registros públicos de adoptante por IP en la misma ventana. Una familia
# o una oficina con una sola IP puede crear varias cuentas; un robot no, cientos.
REGISTROS_MAXIMOS_POR_IP = 5
# P-12 (#285): avisar por correo al dueño cuando alguien intenta registrarse con su correo. Por
# defecto no (como hasta hoy); el aviso sale después de responder, así el tiempo no lo delata.
AVISAR_REGISTRO_DUPLICADO = False
# Auditoría A-02 (#237): reportes públicos por IP en la misma ventana. Generoso: varios
# vecinos pueden compartir la IP del operador móvil; un robot manda cientos.
REPORTES_MAXIMOS_POR_IP = 20

# Auditoría A-01 (#235): topes del reporte público (los mismos de la PWA) y de cualquier
# cuerpo JSON o de formulario. Las subidas de video y fotos tienen sus propios límites.
MAX_CARACTERES_DESCRIPCION = 500
MAX_CARACTERES_DIRECCION = 200
MAX_CUERPO_BYTES = 1024 * 1024

# RNF-06 (#258): horas que dura el enlace de un participante del piloto de usabilidad.
PILOTO_HORAS_VIGENCIA = 24

# RF-17 (#75): dos reportes con GPS a esta distancia y en este rato son posibles duplicados.
DUPLICADO_METROS = 200
DUPLICADO_HORAS = 2

# HU-06 (#46): la zona del rescatista se elige por comunas. El área urbana de Cúcuta tiene
# 10 comunas.
COMUNAS_CUCUTA = tuple(range(1, 11))

# HU-06 (#46, RF-23): minutos sin aceptar, desde la confirmación, antes de avisar al
# coordinador y ofrecer el caso en toda la ciudad. Crítico 15 (decisión del autor); alto 30
# (tabla de configuración del prototipo).
ESCALAMIENTO_MINUTOS = {"critica": 15, "alta": 30}
REVISION_ESCALAMIENTOS_SEGUNDOS = 60

# #63 (outbox): avisos a rescatistas. Reintentos con espera exponencial desde la base; un
# reclamo que no termina en este tiempo (procesador detenido) se vuelve a tomar.
MAX_INTENTOS_AVISO = 5
ESPERA_BASE_AVISO_S = 60
VENCIMIENTO_RECLAMO_AVISO_S = 300
REVISION_AVISOS_SEGUNDOS = 15

# #125 (RF-03, RNF-02): video del reporte, analizado por un trabajador local.
# El ciudadano lo adjunta justo después de crear el reporte, con la misma clave.
VIDEO_VENTANA_SUBIDA_MINUTOS = 30
# El análisis tarda hasta 3 min (RNF-02); un reclamo sin respuesta en 10 min se vuelve a dar.
VENCIMIENTO_RECLAMO_VIDEO_S = 600
MAX_INTENTOS_VIDEO = 3
# Si el trabajador estuvo apagado tanto tiempo, el video se borra y manda el texto.
VIDEO_MAX_ESPERA_HORAS = 6
# #188: videos esperando a la vez (50 MB cada uno): cuida el 1 GB de la base gratis.
MAX_VIDEOS_PENDIENTES = 5
TROZO_VIDEO_BYTES = 1024 * 1024
REVISION_VIDEOS_SEGUNDOS = 60
# Vista previa para el veterinario (cambia RNF-08, #214): MP4 liviano con el esqueleto dibujado.
# Se borra a los 7 días o cuando el reporte se cierra (rescate atendido o descartado).
VISTA_VIDEO_MAX_MB = 5
VISTA_VIDEO_DIAS = 7
