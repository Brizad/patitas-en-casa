"""Cabeceras de seguridad y compresión (#121, hallazgos de OWASP ZAP y de la prueba de punta
a punta en Render)."""
from tests.test_decision_adopcion import en_memoria


def test_cabeceras_de_seguridad_en_todas_las_respuestas():
    c = en_memoria()
    for ruta in ("/app/", "/adopciones/animales", "/reportes/NOEXISTE"):
        r = c.get(ruta)
        assert r.headers["strict-transport-security"] == "max-age=31536000"
        assert "geolocation=(self)" in r.headers["permissions-policy"]
        assert "camera=(self)" in r.headers["permissions-policy"]
        assert "microphone=()" in r.headers["permissions-policy"]
        assert r.headers["cross-origin-opener-policy"] == "same-origin"
        assert r.headers["x-content-type-options"] == "nosniff"


def test_la_pwa_conserva_su_csp_y_se_comprime():
    c = en_memoria()
    r = c.get("/app/app.js", headers={"Accept-Encoding": "gzip"})
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers.get("content-encoding") == "gzip"


# --- OWASP ASVS 4.0.3 nivel 1 (docs/tesis/seguridad.md) ---

def test_asvs_8_2_1_las_respuestas_json_de_la_api_no_se_guardan_en_cache():
    """Datos de reportes, personas y sesiones: ni el navegador ni un proxy deben guardarlos."""
    c = en_memoria()
    for ruta in ("/adopciones/animales", "/reportes/NOEXISTE", "/reportes/NOEXISTE/seguimiento",
                 "/cola", "/auth/yo"):
        assert c.get(ruta).headers["cache-control"] == "no-store", ruta
    sesion = c.post("/auth/token", data={"username": "nadie@patitas.co", "password": "x" * 12})
    assert sesion.headers["cache-control"] == "no-store"


def test_lo_que_ya_decia_como_guardarse_no_cambia():
    """La interfaz estática sí se puede guardar (la PWA funciona sin señal)."""
    c = en_memoria()
    assert c.get("/app/app.js").headers.get("cache-control") != "no-store"


def test_asvs_14_4_ninguna_respuesta_se_puede_enmarcar_ni_filtra_la_direccion():
    """También la API y la documentación: antes solo lo llevaban la PWA y el panel."""
    c = en_memoria()
    for ruta in ("/app/", "/docs", "/adopciones/animales", "/reportes/NOEXISTE"):
        r = c.get(ruta)
        assert r.headers["x-frame-options"] == "DENY", ruta
        assert r.headers["referrer-policy"] == "no-referrer", ruta
