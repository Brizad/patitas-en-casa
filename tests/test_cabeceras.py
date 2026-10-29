"""Cabeceras de seguridad y compresión (#121, hallazgos de OWASP ZAP y de la prueba de punta
a punta en Render)."""
from tests.test_decision_adopcion import en_memoria


def test_cabeceras_de_seguridad_en_todas_las_respuestas():
    c = en_memoria()
    for ruta in ("/app/", "/adopciones/animales", "/reportes/NOEXISTE"):
        r = c.get(ruta)
        assert r.headers["strict-transport-security"] == "max-age=31536000"
        assert "geolocation=(self)" in r.headers["permissions-policy"]
        assert "camera=()" in r.headers["permissions-policy"]
        assert r.headers["cross-origin-opener-policy"] == "same-origin"
        assert r.headers["x-content-type-options"] == "nosniff"


def test_la_pwa_conserva_su_csp_y_se_comprime():
    c = en_memoria()
    r = c.get("/app/app.js", headers={"Accept-Encoding": "gzip"})
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers.get("content-encoding") == "gzip"
