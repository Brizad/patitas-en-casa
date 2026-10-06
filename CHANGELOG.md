# Cambios

Formato basado en *Keep a Changelog*; versiones según SemVer.

## [Sin publicar]
### Corregido
- BUG-02 (#16): la negación se detectaba por subcadena ("vecino", "camino", "pequeño") y degradaba casos críticos; ahora se compara la palabra anterior en cada aparición de la señal.
- BUG-03 (#17): dos clasificaciones colgadas agotaban el pool del triaje; al agotarse el tiempo se descarta el ejecutor y el error queda registrado con logging.
- BUG-04 (#18): dos ingresos simultáneos podían superar la capacidad del refugio; el cupo se comprueba y ocupa bajo un candado y `Refugio` valida 0 ≤ ocupados ≤ capacidad.
### Agregado
- Prueba del tiempo agotado del triaje (PA-02) y pruebas de regresión de BUG-02, BUG-03 y BUG-04 (40 pruebas, 97 % de cobertura).

## [0.1.0] - 2026-09-29
### Agregado
- Registro de reportes de emergencia sin cuenta, con validaciones (RF-01, HU-01).
- Triaje por texto con clasificador de reglas v0, política de baja confianza y falla segura (RF-02, RNF-03).
- Cola priorizada con control de rol (RF-04, HU-02).
- Registro de ingresos, control de cupos y alerta al 90 % (RF-06, RF-07, HU-03).
- API REST con FastAPI y pipeline de CI (build, lint, test).
### Corregido
- BUG-01: señales con tilde no se detectaban en el triaje.
