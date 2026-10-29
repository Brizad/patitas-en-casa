"""Asignación global en jornadas de adopción (RF-28, fase 4, #95).

Problema: en una jornada hay varios adoptantes y varios animales. Si cada coordinador elige
«el mejor animal para cada persona» de uno en uno (algoritmo voraz), el primero se queda con
el animal que mejor encajaba con otro, y el total empeora. Queremos la combinación (cada
persona con a lo sumo un animal y al revés) que maximiza la suma de compatibilidades.

Eso es el «problema de asignación» y lo resuelve el algoritmo húngaro en O(n³): para una
jornada de decenas de personas son milisegundos, sin librerías. Las parejas con una
restricción dura (puntaje 0) no se proponen.

El resultado es una PROPUESTA (RN-16: la IA sugiere, la persona decide): el coordinador la
revisa y aprueba o rechaza cada solicitud como siempre.
"""
from __future__ import annotations


def hungaro(costos: list[list[float]]) -> list[int]:
    """Asignación de costo mínimo en una matriz cuadrada n×n.

    Devuelve asignada[i] = columna de la fila i. Versión con potenciales (u, v): en cada
    paso agrega una fila y busca el camino de aumento más barato (como Dijkstra).
    """
    n = len(costos)
    infinito = float("inf")
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
    fila_de = [0] * (n + 1)  # fila_de[j]: fila asignada a la columna j (1..n); 0 = libre
    for i in range(1, n + 1):
        fila_de[0], j0 = i, 0
        minimo, previo = [infinito] * (n + 1), [0] * (n + 1)
        usada = [False] * (n + 1)
        while fila_de[j0]:
            usada[j0] = True
            i0, delta, j1 = fila_de[j0], infinito, 0
            for j in range(1, n + 1):
                if not usada[j]:
                    actual = costos[i0 - 1][j - 1] - u[i0] - v[j]
                    if actual < minimo[j]:
                        minimo[j], previo[j] = actual, j0
                    if minimo[j] < delta:
                        delta, j1 = minimo[j], j
            for j in range(n + 1):
                if usada[j]:
                    u[fila_de[j]] += delta
                    v[j] -= delta
                else:
                    minimo[j] -= delta
            j0 = j1
        while j0:  # recorre el camino de aumento al revés
            j1 = previo[j0]
            fila_de[j0] = fila_de[j1]
            j0 = j1
    asignada = [0] * n
    for j in range(1, n + 1):
        if fila_de[j]:
            asignada[fila_de[j] - 1] = j - 1
    return asignada


def asignar(puntajes: list[list[int]]) -> list[tuple[int, int]]:
    """Parejas (adoptante, animal) que maximizan la suma de puntajes; omite los de 0.

    Para maximizar con un algoritmo que minimiza se usa costo = máximo − puntaje, y la
    matriz se completa con filas o columnas «vacías» (puntaje 0) hasta ser cuadrada.
    """
    if not puntajes or not puntajes[0]:
        return []
    filas, columnas = len(puntajes), len(puntajes[0])
    n = max(filas, columnas)
    tope = max(max(fila) for fila in puntajes)
    costos = [[tope - (puntajes[i][j] if i < filas and j < columnas else 0)
               for j in range(n)] for i in range(n)]
    return [(i, j) for i, j in enumerate(hungaro(costos))
            if i < filas and j < columnas and puntajes[i][j] > 0]
