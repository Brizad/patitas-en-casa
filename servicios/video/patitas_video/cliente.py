"""Cliente de la API de Render para el trabajador local de video (#125).

El trabajador nunca recibe conexiones: él llama a la API (así funciona detrás del router de
la casa, sin abrir puertos). Se identifica con el encabezado X-Video-Token. El token no se
escribe en los logs.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from patitas_video import __version__


class ApiNoDisponible(RuntimeError):
    """Render dormido, sin red o error 5xx: se reintenta más tarde."""


class TrabajoPerdido(RuntimeError):
    """El trabajo ya no existe, ya se cerró o su video se perdió: se pasa al siguiente."""


class ClienteApi:
    def __init__(self, url: str, token: str, http: httpx.Client | None = None,
                 espera_s: float = 90) -> None:
        # 90 s: el plan gratis de Render tarda hasta un minuto en despertar.
        self._http = http or httpx.Client(timeout=espera_s)
        self._url = url.rstrip("/")
        # #231: la versión viaja en cada llamada; así la API sabe si este nodo quedó viejo.
        self._encabezados = {"X-Video-Token": token, "X-Video-Nodo": __version__}

    def _pedir(self, metodo: str, ruta: str, **opciones) -> httpx.Response:
        try:
            encabezados = {**self._encabezados, **opciones.pop("headers", {})}
            respuesta = self._http.request(metodo, self._url + ruta,
                                           headers=encabezados, **opciones)
        except httpx.HTTPError as error:
            raise ApiNoDisponible(f"sin conexión con la API: {type(error).__name__}") from error
        if respuesta.status_code >= 500:
            raise ApiNoDisponible(f"la API respondió {respuesta.status_code}")
        if respuesta.status_code == 401:
            raise PermissionError("PATITAS_VIDEO_TOKEN no coincide con el de Render.")
        if respuesta.status_code in (404, 409, 410):
            raise TrabajoPerdido(respuesta.json().get("detail", str(respuesta.status_code)))
        respuesta.raise_for_status()
        return respuesta

    def reclamar(self) -> dict | None:
        respuesta = self._pedir("POST", "/video/trabajos/reclamar")
        return None if respuesta.status_code == 204 else respuesta.json()

    def descargar(self, id_: int, destino: Path) -> None:
        """Por partes, sin cargar los 50 MB en memoria."""
        try:
            with self._http.stream("GET", f"{self._url}/video/trabajos/{id_}/archivo",
                                   headers=self._encabezados) as respuesta:
                if respuesta.status_code in (404, 409, 410):
                    raise TrabajoPerdido(f"el video {id_} ya no está disponible")
                if respuesta.status_code >= 400:
                    raise ApiNoDisponible(f"la API respondió {respuesta.status_code}")
                with destino.open("wb") as archivo:
                    for trozo in respuesta.iter_bytes():
                        archivo.write(trozo)
        except httpx.HTTPError as error:
            raise ApiNoDisponible(f"descarga interrumpida: {type(error).__name__}") from error

    def subir_vista(self, id_: int, mp4: bytes) -> None:
        """La vista previa del veterinario (MP4 de ≤ 5 MB), antes de entregar el resultado."""
        self._pedir("POST", f"/video/trabajos/{id_}/vista", content=mp4,
                    headers={"Content-Type": "video/mp4"})

    def entregar(self, id_: int, resultado: dict) -> dict:
        return self._pedir("POST", f"/video/trabajos/{id_}/resultado", json=resultado).json()

    def fallar(self, id_: int, motivo: str) -> dict:
        return self._pedir("POST", f"/video/trabajos/{id_}/fallo",
                           json={"motivo": motivo[:300]}).json()
