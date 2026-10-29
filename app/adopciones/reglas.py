"""Restricciones duras de adopción (RN-05, #85).

Una restricción dura no se negocia con un buen puntaje: si el animal no puede convivir con
niños y en la casa hay niños, la adopción no se aprueba. Se usa al aprobar (fase 3) y al
recomendar (fase 4: un animal con restricción dura no se recomienda).
"""
from __future__ import annotations

from app.adopciones.modelos import PerfilAdoptante, Publicacion


def restricciones_duras(perfil: PerfilAdoptante, publicacion: Publicacion) -> list[str]:
    """Motivos por los que esta adopción no puede aprobarse; vacío = no hay restricción."""
    motivos = []
    if perfil.hay_ninos and not publicacion.apto_ninos:
        motivos.append("el animal no es apto para convivir con niños y en el hogar hay niños")
    if perfil.otros_animales and not publicacion.apto_otros_animales:
        motivos.append("el animal no convive con otros animales y en el hogar hay otros")
    if publicacion.necesita_patio and not perfil.tiene_patio:
        motivos.append("el animal necesita patio y el hogar no tiene")
    return motivos
