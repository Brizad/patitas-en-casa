"""Auditoría A-01 (#235): límites de tamaño en el reporte público y en los cuerpos JSON."""
from app import config
from tests.test_api import cliente

UBICACION = {"direccion": "Calle 10 #5-20, Cúcuta"}
TEXTO = "Perro atropellado que no se puede levantar y sangra mucho "


def test_la_descripcion_de_500_caracteres_pasa_y_la_de_501_no():
    c = cliente()
    texto = (TEXTO * 10)[:500]
    assert c.post("/reportes", json={"descripcion": texto, **UBICACION}).status_code == 201
    r = c.post("/reportes", json={"descripcion": texto + "x", **UBICACION})
    assert r.status_code == 422


def test_la_direccion_de_mas_de_200_caracteres_se_rechaza():
    r = cliente().post("/reportes", json={"descripcion": TEXTO, "direccion": "a" * 201})
    assert r.status_code == 422


def test_un_cuerpo_json_de_mas_de_un_mega_se_rechaza_sin_leerlo():
    grande = "x" * (config.MAX_CUERPO_BYTES + 1)
    r = cliente().post("/reportes", content=grande,
                       headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert "grande" in r.json()["detail"]


def _por_partes(total: int, trozo: int = 64 * 1024):
    """Cuerpo sin Content-Length: httpx lo manda con Transfer-Encoding: chunked."""
    while total > 0:
        yield b"x" * min(trozo, total)
        total -= trozo


def test_a08_un_cuerpo_chunked_de_mas_de_un_mega_tambien_se_rechaza():
    r = cliente().post("/reportes", content=_por_partes(config.MAX_CUERPO_BYTES + 1),
                       headers={"Content-Type": "application/json"})
    assert "content-length" not in r.request.headers
    assert r.status_code == 413
    assert "grande" in r.json()["detail"]


def test_a08_un_reporte_chunked_pequeno_pasa():
    import json
    cuerpo = json.dumps({"descripcion": TEXTO, **UBICACION}).encode()
    r = cliente().post("/reportes", content=iter([cuerpo[:20], cuerpo[20:]]),
                       headers={"Content-Type": "application/json"})
    assert "content-length" not in r.request.headers
    assert r.status_code == 201


def test_el_limite_no_aplica_a_las_subidas_de_video_ni_de_fotos():
    from app.api.middlewares import es_subida_de_archivo
    assert es_subida_de_archivo("/reportes/ABCD1234/video")
    assert es_subida_de_archivo("/video/trabajos/7/vista")
    assert es_subida_de_archivo("/refugio/animales/3/foto")
    assert not es_subida_de_archivo("/reportes")
    assert not es_subida_de_archivo("/auth/token")
