"""A-04 / DT-11 (#278): IP real del cliente detrás de proxies, configurable y no falsificable."""
from types import SimpleNamespace

import pytest

from app.ajustes import AjustesIp
from app.api.comun import ip_del_cliente
from tests.test_api import sesion
from tests.test_piloto import cliente_con_admin


def peticion(conexion="10.0.0.9", **encabezados):
    return SimpleNamespace(client=SimpleNamespace(host=conexion) if conexion else None,
                           headers={k.lower().replace("_", "-"): v
                                    for k, v in encabezados.items()})


def test_por_defecto_es_la_ip_de_la_conexion_como_antes():
    p = peticion(x_forwarded_for="1.1.1.1, 200.1.2.3")
    assert ip_del_cliente(p, AjustesIp()) == "10.0.0.9"
    assert ip_del_cliente(peticion(conexion=None), AjustesIp()) == "desconocida"


def test_con_un_proxy_de_confianza_toma_la_ultima_entrada_y_no_la_que_inventa_el_cliente():
    # El cliente manda «1.1.1.1»; el proxy de confianza agrega la IP real al final.
    p = peticion(x_forwarded_for="1.1.1.1, 200.1.2.3")
    assert ip_del_cliente(p, AjustesIp(proxies_confianza=1)) == "200.1.2.3"
    assert ip_del_cliente(p, AjustesIp(proxies_confianza=2)) == "1.1.1.1"


def test_si_faltan_entradas_no_se_inventa_nada():
    p = peticion(x_forwarded_for="200.1.2.3")
    assert ip_del_cliente(p, AjustesIp(proxies_confianza=2)) == "10.0.0.9"
    assert ip_del_cliente(peticion(), AjustesIp(proxies_confianza=1)) == "10.0.0.9"


def test_un_encabezado_que_escribe_el_proxy_tiene_prioridad():
    p = peticion(x_forwarded_for="1.1.1.1, 200.1.2.3", cf_connecting_ip="190.5.6.7")
    ajustes = AjustesIp(encabezado_ip="CF-Connecting-IP", proxies_confianza=1)
    assert ip_del_cliente(p, ajustes) == "190.5.6.7"
    sin_el = peticion(x_forwarded_for="1.1.1.1, 200.1.2.3")
    assert ip_del_cliente(sin_el, ajustes) == "200.1.2.3"  # si falta, sigue con XFF


@pytest.mark.parametrize("valor", [-1, 6])
def test_el_numero_de_proxies_es_razonable(valor):
    with pytest.raises(ValueError):
        AjustesIp(proxies_confianza=valor)


def test_el_encabezado_debe_ser_un_nombre_de_encabezado():
    with pytest.raises(ValueError):
        AjustesIp(encabezado_ip="CF-Connecting-IP: 1.2.3.4")


def test_diagnostico_solo_para_el_administrador_y_sin_datos_sensibles():
    c = cliente_con_admin()
    assert c.get("/admin/diagnostico/ip").status_code == 401
    assert c.get("/admin/diagnostico/ip", headers=sesion(c)).status_code == 403
    admin = sesion(c, "admin@patitas.co")
    r = c.get("/admin/diagnostico/ip", headers={
        **admin, "X-Forwarded-For": "1.1.1.1, 200.1.2.3", "CF-Connecting-IP": "190.5.6.7",
        "Cookie": "secreto=1"})
    datos = r.json()
    assert r.status_code == 200
    assert datos["x_forwarded_for"] == ["1.1.1.1", "200.1.2.3"]
    assert datos["encabezados"]["cf-connecting-ip"] == "190.5.6.7"
    assert datos["ip_usada"] == datos["ip_conexion"]  # por defecto, como antes
    texto = r.text.lower()
    assert "bearer" not in texto and "secreto" not in texto and "authorization" not in texto


def test_el_limite_de_reportes_usa_la_ip_configurada():
    """A-02 con un proxy de confianza: cambiar la primera entrada de XFF ya no esquiva el límite."""
    from app import config
    c = cliente_con_admin(ajustes_ip=AjustesIp(proxies_confianza=1))
    cuerpo = {"descripcion": "Perro atropellado que no se puede levantar", "direccion": "Calle 10"}
    for n in range(config.REPORTES_MAXIMOS_POR_IP):
        r = c.post("/reportes", json=cuerpo, headers={"X-Forwarded-For": f"9.9.9.{n}, 200.1.2.3"})
        assert r.status_code == 201
    r = c.post("/reportes", json=cuerpo, headers={"X-Forwarded-For": "8.8.8.8, 200.1.2.3"})
    assert r.status_code == 429
