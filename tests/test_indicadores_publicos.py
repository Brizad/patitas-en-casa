"""#426: la portada muestra tres totales anónimos sin sesión; nunca datos por persona."""
from app import config
from tests.test_decision_adopcion import en_memoria, h, preparar


def test_tres_totales_publicos_y_nada_mas(monkeypatch):
    monkeypatch.setattr(config, "CACHE_INDICADORES_PUBLICOS_S", 0)
    c = en_memoria()
    assert c.get("/indicadores/publicos").json() == {"reportes": 0, "rescatados": 0,
                                                     "adoptados": 0}
    coord, _, ids = preparar(c)
    c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision", json={"aprobar": True},
           headers=coord)
    c.post("/reportes", json={"descripcion": "Perro herido en la esquina del parque central",
                              "latitud": 7.89, "longitud": -72.5})
    cifras = c.get("/indicadores/publicos").json()  # sin sesión
    assert cifras == {"reportes": 1, "rescatados": 0, "adoptados": 1}
    assert h  # el adoptante no necesita entrar para verlas


def test_se_recalculan_como_mucho_cada_cierto_tiempo(monkeypatch):
    monkeypatch.setattr(config, "CACHE_INDICADORES_PUBLICOS_S", 3600)
    c = en_memoria()
    assert c.get("/indicadores/publicos").json()["reportes"] == 0
    c.post("/reportes", json={"descripcion": "Gato atropellado frente a la tienda del barrio",
                              "latitud": 7.89, "longitud": -72.5})
    assert c.get("/indicadores/publicos").json()["reportes"] == 0  # aún la copia guardada
