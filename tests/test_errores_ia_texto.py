"""#245: el recall de crítica con textos de ciudadano no puede bajar (textos del asistente)."""
from pathlib import Path

import pytest

from scripts.ia.analizar_errores import POR_DEFECTO, evaluar


@pytest.mark.parametrize("ruta", [POR_DEFECTO, POR_DEFECTO.with_name(
    "casos_ciudadanos_control.json")])
def test_ninguna_critica_de_los_casos_ciudadanos_queda_por_debajo_de_critica(ruta: Path):
    resultado = evaluar(ruta)
    assert resultado["recall_critica"] == 1.0, resultado["errores"]
