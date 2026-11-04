from app.triaje.normalizacion import normalizar


def test_quita_tildes_mayusculas_y_espacios():
    assert normalizar("  Convulsión  y VÓMITO ") == "convulsion y vomito"


def test_conserva_la_enie_sin_tilde():
    assert normalizar("Pequeño") == "pequeno"


def test_rr_al_inicio_de_palabra_se_corrige_sin_tocar_las_demas():
    """#245: «no rrespira» se escribe así en el teclado del celular; «perro» no cambia."""
    from app.triaje.normalizacion import normalizar
    assert normalizar("El perro NO RRESPIRA") == "el perro no respira"
