from app.triaje.normalizacion import normalizar


def test_quita_tildes_mayusculas_y_espacios():
    assert normalizar("  Convulsión  y VÓMITO ") == "convulsion y vomito"


def test_conserva_la_enie_sin_tilde():
    assert normalizar("Pequeño") == "pequeno"
