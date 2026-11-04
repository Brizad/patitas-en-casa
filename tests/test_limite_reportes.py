"""Auditoría A-02 (#237): máximo de reportes públicos por IP en la ventana (429)."""
from app import config
from tests.test_api import cliente

TEXTO = "Perro atropellado que no se puede levantar y sangra mucho"


def reportar(c, n, clave=None):
    cabeceras = {"Idempotency-Key": clave} if clave else {}
    return c.post("/reportes", headers=cabeceras,
                  json={"descripcion": f"{TEXTO} caso {n}", "direccion": "Calle 10 #5-20"})


def test_pasado_el_maximo_por_ip_responde_429_con_retry_after():
    c = cliente()
    for n in range(config.REPORTES_MAXIMOS_POR_IP):
        assert reportar(c, n).status_code == 201
    r = reportar(c, 99)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert "emergencia" in r.json()["detail"]


def test_reenviar_el_mismo_reporte_no_cuenta_ni_se_bloquea():
    c = cliente()
    clave = "clave-de-la-pwa-0001"
    for _ in range(config.REPORTES_MAXIMOS_POR_IP + 5):  # la cola sin conexión reintenta
        assert reportar(c, 1, clave).status_code in (200, 201)
    assert reportar(c, 2).status_code == 201  # los reintentos no gastaron el cupo


def test_un_reporte_rechazado_por_la_validacion_tambien_cuenta():
    c = cliente()
    for _ in range(config.REPORTES_MAXIMOS_POR_IP):
        c.post("/reportes", json={"descripcion": "corto", "direccion": "Calle 10"})
    assert reportar(c, 1).status_code == 429
