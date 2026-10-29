"""Parámetros de negocio del MVP (línea base de requisitos v1.1)."""

# RNF-03: por debajo de esta confianza el reporte exige revisión humana.
UMBRAL_CONFIANZA = 0.6

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
REVISION_VIDEOS_SEGUNDOS = 60
