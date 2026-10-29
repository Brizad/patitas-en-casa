"""Texto del compromiso de adopción responsable (RF-29, #85).

Es un documento para imprimir y firmar en el refugio: el sistema no recoge firmas
electrónicas. Los compromisos vienen de RN-12 (seguimientos) y RN-13 (devolución al refugio
en vez de abandonar).
"""
from __future__ import annotations

from datetime import UTC

from app.adopciones.modelos import Publicacion, Seguimiento, Solicitud
from app.dominio.modelos import Refugio

COMPROMISOS = [
    "Darle alimento adecuado, agua limpia y un lugar protegido del sol y la lluvia.",
    "Llevarlo al veterinario cuando lo necesite y mantener sus vacunas al día.",
    "Esterilizarlo si aún no lo está, en el plazo que indique el refugio.",
    "No abandonarlo ni regalarlo: si ya no puedo cuidarlo, lo devuelvo al refugio (RN-13).",
    "Permitir los seguimientos del refugio a los 30, 90 y 180 días (RF-10, RN-12).",
    "No usarlo para peleas, cría comercial ni trabajos que le causen daño.",
]


def lineas_compromiso(solicitud: Solicitud, publicacion: Publicacion, nombre_adoptante: str,
                      seguimientos: list[Seguimiento],
                      refugio: Refugio | None = None) -> list[str | tuple[str, int]]:
    fecha = solicitud.decidida_en.astimezone(UTC).strftime("%Y-%m-%d")
    lineas: list[str | tuple[str, int]] = [
        ("Compromiso de adopción responsable", 18),
        "Patitas en Casa · Cúcuta, Norte de Santander",
        "",
        f"Solicitud N.° {solicitud.id} · aprobada el {fecha} (UTC)",
        f"Animal: {publicacion.nombre} ({publicacion.especie}), {publicacion.edad_meses} meses",
        f"Adoptante: {nombre_adoptante} <{solicitud.adoptante}>",
        f"Refugio: {refugio.nombre}" + (f", {refugio.direccion}" if refugio.direccion else "")
        if refugio else "Refugio: sin dato",
        "",
        ("Me comprometo a:", 13),
    ]
    lineas += [f"{i}. {texto}" for i, texto in enumerate(COMPROMISOS, start=1)]
    lineas += ["", ("Seguimientos programados", 13)]
    lineas += [f"- Día {x.dia}: {x.programado_para.astimezone(UTC):%Y-%m-%d}"
               for x in seguimientos]
    lineas += ["", "", "Firma del adoptante: ______________________________",
               "", "Firma del refugio:   ______________________________", "",
               "Documento generado por Patitas en Casa. Se firma a mano en el refugio."]
    return lineas
