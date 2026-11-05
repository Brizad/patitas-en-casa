"""Genera el rastro de huellas de la portada (#328): posiciones sobre la curva, sin JavaScript.

La página no puede calcular nada (CSP sin scripts), así que las huellas se ubican aquí y se pegan
en `app/inicio/index.html`. Perro y gato caminan juntos a lo largo de la curva: el perro por
encima, el gato por debajo, cada huella alternando izquierda y derecha como pasos de verdad.
La clase `tN` dice en qué momento aparece (la animación está en `inicio.css`) y `banda` marca
las que pisan la banda oscura (van en crema).

Uso: python scripts/diseno/rastro.py  →  imprime las líneas <g> del rastro.
"""
import math

# Dos tramos cúbicos (viewBox 0 0 1440 320): baja, sube al centro (la píldora) y vuelve a bajar.
TRAMOS = [((-40, 270), (240, 10), (470, 330), (720, 170)),
          ((720, 170), (970, 10), (1200, 320), (1480, 70))]
CURVA = "M-40 270C240 10 470 330 720 170S1200 320 1480 70"  # el mismo trazo, para el <path>
BANDA = (848, 1112)       # x de la banda oscura
PILDORA = (624, 816)      # x de la píldora del centro: ahí no se pisa
TIEMPOS = 16              # ranuras de tiempo de la caminata (.t0 … .t15)


def punto(t, p0, p1, p2, p3):
    u = 1 - t
    return tuple(u**3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t**3 * d
                 for a, b, c, d in zip(p0, p1, p2, p3, strict=True))


def muestras(n=400):
    puntos = [punto(i / n, *tramo) for tramo in TRAMOS for i in range(n + 1)]
    largo, acumulado = 0.0, [0.0]
    for a, b in zip(puntos, puntos[1:], strict=False):
        largo += math.dist(a, b)
        acumulado.append(largo)
    return puntos, acumulado


def en(distancia, puntos, acumulado):
    """Punto y ángulo de avance (grados) a una distancia dada sobre la curva."""
    i = next((k for k, d in enumerate(acumulado) if d >= distancia), len(puntos) - 1)
    i = max(i, 1)
    (x0, y0), (x1, y1) = puntos[i - 1], puntos[i]
    return (x1, y1), math.degrees(math.atan2(y1 - y0, x1 - x0))


def rastro(especie, separacion, lado, paso, inicio, tamano):
    puntos, acumulado = muestras()
    lineas, d, n = [], inicio, 0
    while d < acumulado[-1]:
        (x, y), angulo = en(d, puntos, acumulado)
        normal = math.radians(angulo - 90)  # hacia arriba de la marcha
        desvio = lado + (paso if n % 2 else -paso)  # izquierda y derecha alternadas
        hx, hy = x + desvio * math.cos(normal), y + desvio * math.sin(normal)
        if 0 < hx < 1440 and not PILDORA[0] < hx < PILDORA[1]:
            tiempo = min(TIEMPOS - 1, int(hx / 1440 * TIEMPOS))
            clases = f"{especie} t{tiempo}" + (" banda" if BANDA[0] < hx < BANDA[1] else "")
            giro = angulo + 90 + (8 if n % 2 else -8)  # la huella apunta hacia donde camina
            lineas.append(f'<g transform="translate({hx:.0f} {hy:.0f}) rotate({giro:.0f}) scale({tamano})">'
                          f'<use class="{clases}" href="#huella-{especie}"/></g>')
        d += separacion
        n += 1
    return lineas


if __name__ == "__main__":
    print(f'<path class="camino" d="{CURVA}"/>')
    print("\n".join(rastro("perro", 118, 38, 14, 30, 1.5) + rastro("gato", 100, -38, 10, 60, 1.25)))
