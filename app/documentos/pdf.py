"""PDF de texto sencillo, sin dependencias (RF-29, #85; también sirve a RF-31).

¿Por qué escribirlo a mano? Una librería como ReportLab pesa varios MB y el plan gratis de
Render tiene 512 MB de RAM. Un PDF de solo texto es un formato sencillo: objetos numerados
(catálogo, páginas, fuente y el contenido de cada página) y una tabla «xref» con la posición
en bytes de cada objeto, que el lector usa para encontrarlos.

Se usa la fuente Helvetica (viene en todo lector de PDF) con WinAnsiEncoding, que incluye
las tildes y la ñ del español.
"""
from __future__ import annotations

ALTO_PAGINA = 842  # A4 en puntos (1/72 de pulgada)
ANCHO_PAGINA = 595
MARGEN = 56
INTERLINEA = 16
LINEAS_POR_PAGINA = (ALTO_PAGINA - 2 * MARGEN) // INTERLINEA


def _escapar(texto: str) -> bytes:
    """Los paréntesis y la barra invertida delimitan cadenas en PDF: se escapan."""
    texto = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # cp1252 = WinAnsiEncoding; un carácter fuera de ella se cambia por «?».
    return texto.encode("cp1252", errors="replace")


def _contenido(lineas: list[tuple[str, int]]) -> bytes:
    partes = [b"BT"]
    y = ALTO_PAGINA - MARGEN
    for texto, tamano in lineas:
        partes.append(b"/F1 %d Tf 1 0 0 1 %d %d Tm (" % (tamano, MARGEN, y)
                      + _escapar(texto) + b") Tj")
        y -= INTERLINEA if tamano <= 12 else INTERLINEA + 8
    partes.append(b"ET")
    return b"\n".join(partes)


def generar_pdf(lineas: list[str | tuple[str, int]]) -> bytes:
    """Una línea por elemento; (texto, tamaño) para un título. Pagina sola."""
    normalizadas = [(x, 11) if isinstance(x, str) else x for x in lineas] or [("", 11)]
    paginas = [normalizadas[i:i + LINEAS_POR_PAGINA]
               for i in range(0, len(normalizadas), LINEAS_POR_PAGINA)]
    # Objetos: 1 catálogo, 2 árbol de páginas, 3 fuente; luego página y contenido por página.
    ids_paginas = [4 + 2 * i for i in range(len(paginas))]
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % i for i in ids_paginas)
        + b"] /Count %d >>" % len(paginas),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for pagina, id_pagina in zip(paginas, ids_paginas, strict=True):
        flujo = _contenido(pagina)
        objetos.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
                       b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
                       % (ANCHO_PAGINA, ALTO_PAGINA, id_pagina + 1))
        objetos.append(b"<< /Length %d >>\nstream\n" % len(flujo) + flujo + b"\nendstream")

    salida = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % numero + cuerpo + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    salida += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
               % (len(objetos) + 1, inicio_xref))
    return bytes(salida)
