"""ASVS 4.1 (control de acceso): se niega por defecto. Esta prueba recorre TODAS las rutas del
OpenAPI sin sesión: solo las públicas declaradas aquí pueden responder; cualquier otra debe
dar 401. Una ruta nueva sin `dependencies=[personal]` hace fallar esta prueba."""
import re

from fastapi.testclient import TestClient

from scripts.tesis.generar_docs import _app

# Lo que un ciudadano o un adoptante sin cuenta puede usar (CLAUDE.md, «Seguridad»).
PUBLICAS = {
    ("POST", "/reportes"), ("GET", "/reportes/{codigo}"),
    ("GET", "/reportes/{codigo}/seguimiento"), ("POST", "/auth/token"), ("POST", "/adoptantes"),
    ("GET", "/adopciones/animales"), ("GET", "/adopciones/animales/{animal_id}/foto"),
    ("POST", "/piloto/reportes"), ("POST", "/piloto/resultados"),
    ("GET", "/indicadores/publicos"),  # #426: tres totales anónimos para la portada
}
# No piden sesión pero tampoco son abiertas: exigen la clave del reporte (403 sin ella).
CON_CLAVE_PROPIA = {("POST", "/reportes/{codigo}/video")}


def _sin_sesion():
    app = _app()
    cliente = TestClient(app)
    for ruta, metodos in app.openapi()["paths"].items():
        for metodo in metodos:
            respuesta = cliente.request(metodo.upper(), re.sub(r"\{[^}]+\}", "1", ruta))
            yield (metodo.upper(), ruta), respuesta.status_code


def test_sin_sesion_solo_responden_las_rutas_publicas_declaradas():
    estados = dict(_sin_sesion())
    abiertas = {ruta for ruta, estado in estados.items() if estado not in (401, 403)}
    assert abiertas == PUBLICAS
    assert {ruta for ruta, estado in estados.items() if estado == 403} == CON_CLAVE_PROPIA
    assert len(estados) > 70  # se recorrió el catálogo completo, no una lista a mano


def test_las_rutas_publicas_no_devuelven_datos_personales_sin_pedirlos():
    """Lo público responde con error de validación o «no existe», nunca con datos ajenos."""
    estados = dict(_sin_sesion())
    assert estados[("GET", "/reportes/{codigo}")] == 404
    assert estados[("GET", "/reportes/{codigo}/seguimiento")] == 404
    assert estados[("POST", "/auth/token")] == 422
