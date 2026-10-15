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

# DT-06: intentos fallidos de inicio de sesión permitidos dentro de la ventana. Por IP el
# máximo es mayor porque el personal de un refugio suele compartir la misma IP pública.
INTENTOS_MAXIMOS = 5
INTENTOS_MAXIMOS_POR_IP = 20
VENTANA_INTENTOS_MINUTOS = 15
