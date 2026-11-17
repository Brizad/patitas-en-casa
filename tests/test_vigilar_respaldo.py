"""Vigilancia del respaldo diario (RNF-15): versión de pg_dump contra la del servidor y alerta
si el último respaldo guardado tiene más de 26 horas."""
import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.operacion.vigilar_respaldo import (
    MAX_HORAS,
    main,
    revisar_respaldos,
    revisar_version,
)

AHORA = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


def artefacto(nombre: str, hace_horas: float, vencido: bool = False) -> dict:
    creado = AHORA - timedelta(hours=hace_horas)
    return {"name": nombre, "created_at": creado.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expired": vencido}


def test_un_respaldo_de_hoy_esta_bien():
    bien, mensaje = revisar_respaldos([artefacto("respaldo-1", 5), artefacto("respaldo-0", 29)],
                                      AHORA)
    assert bien and "hace 5 h" in mensaje


def test_justo_26_horas_todavia_vale_y_27_ya_alerta():
    assert MAX_HORAS == 26
    assert revisar_respaldos([artefacto("respaldo-1", 26)], AHORA)[0]
    bien, mensaje = revisar_respaldos([artefacto("respaldo-1", 27)], AHORA)
    assert not bien and "27 h" in mensaje and "más de 26" in mensaje


def test_sin_ningun_respaldo_alerta():
    bien, mensaje = revisar_respaldos([], AHORA)
    assert not bien and "No hay ningún respaldo" in mensaje


def test_solo_cuentan_los_respaldos_que_aun_se_pueden_descargar():
    """Un artefacto vencido (más de 14 días) o de otro flujo no es un respaldo disponible."""
    otros = [artefacto("respaldo-9", 2, vencido=True), artefacto("informe-accesibilidad", 1),
             artefacto("e2e-capturas", 1)]
    assert not revisar_respaldos(otros, AHORA)[0]


@pytest.mark.parametrize(("servidor", "cliente", "bien"), [
    ("180001", "18", True),    # Neon 18.1 con pg_dump 18
    ("170006", "18", True),    # un cliente más nuevo que el servidor sirve
    ("190000", "18", False),   # Neon se actualizó: pg_dump 18 no puede con PostgreSQL 19
    ("180001", "17", False),   # lo que pasó en #210
])
def test_pg_dump_debe_ser_de_la_version_del_servidor_o_mayor(servidor, cliente, bien):
    resultado, mensaje = revisar_version(servidor, cliente)
    assert resultado is bien
    if not bien:
        mayor = int(servidor) // 10000
        assert f'PG_VERSION: "{mayor}"' in mensaje and "respaldo.yml" in mensaje


def test_una_version_ilegible_se_dice_claro_y_no_revienta():
    bien, mensaje = revisar_version("", "18")
    assert not bien and "No se pudo leer la versión del servidor" in mensaje


def test_el_comando_sale_con_1_y_un_error_de_actions_cuando_alerta(tmp_path, capsys):
    archivo = tmp_path / "artefactos.json"
    archivo.write_text(json.dumps({"artifacts": [artefacto("respaldo-1", 40)]}), "utf-8")
    assert main(["respaldos", str(archivo)], ahora=AHORA) == 1
    assert capsys.readouterr().out.startswith("::error::")
    assert main(["version", "180001", "18"]) == 0
    assert main(["version", "190000", "18"]) == 1
