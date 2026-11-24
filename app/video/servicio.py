"""Casos de uso del video del reporte (#125, RF-03, RF-19, RN-07, RNF-02).

1. El ciudadano adjunta el video justo después de crear el reporte (solo él tiene la clave de
   idempotencia con la que lo creó).
2. El trabajador local reclama el trabajo, descarga el video y devuelve el resultado.
3. Aquí se aplica RN-07 (gana la prioridad más alta) sin tocar lo que ya decidió el
   veterinario, se registra la discrepancia (RF-19) y se borra el video.

Falla segura: si el video se pierde, no es concluyente o nadie lo analiza a tiempo, el reporte
sigue con la prioridad del texto.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app import config
from app.dominio.modelos import DECIDIDOS, EstadoReporte
from app.reportes.repositorio import RepositorioReportes
from app.triaje.clasificador import Resultado
from app.triaje.video import aplicar_video
from app.video.modelos import EstadoVideo, ResultadoVideo, TrabajoVideo
from app.video.repositorio import RepositorioVideos


class VideoRechazado(Exception):
    def __init__(self, estado_http: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http


def version_al_dia(version: str | None) -> bool:
    """#231: ¿el nodo corre al menos la versión que esta API espera? Sin versión, es viejo."""
    try:
        return (tuple(int(p) for p in (version or "").split("."))
                >= tuple(int(p) for p in config.VERSION_MINIMA_NODO_VIDEO.split(".")))
    except ValueError:
        return False


class AlmacenVideos(Protocol):
    def existe(self, ruta: str) -> bool: ...
    def borrar(self, ruta: str) -> None: ...
    def purgar_antes_de(self, limite: datetime) -> int: ...


class ServicioVideo:
    def __init__(self, videos: RepositorioVideos, reportes: RepositorioReportes,
                 almacen: AlmacenVideos, reloj: Callable[[], datetime] | None = None,
                 almacen_vistas: AlmacenVideos | None = None,
                 rescate_atendido: Callable[[str], bool] | None = None) -> None:
        self._videos, self._reportes, self._almacen = videos, reportes, almacen
        self._vistas = almacen_vistas  # None: sin vista previa
        self._rescate_atendido = rescate_atendido or (lambda _codigo: False)
        self._reloj = reloj or (lambda: datetime.now(UTC))
        # #231: último contacto del nodo. En memoria: el nodo consulta cada 15 s, así que tras
        # un reinicio de la API se vuelve a saber enseguida.
        self._contacto: datetime | None = None
        self._version_nodo: str | None = None
        self._ocupado_hasta: datetime | None = None
        # #390: el nodo pregunta cada 15 s a 5 min y cada pregunta despertaba la base de Neon.
        # Un trabajo entra a la cola por esta API (subida, fallo con reintento) o porque vence un
        # reclamo. Tras un reclamo vacío se responde sin consultar hasta que pase algo de eso.
        self._inicio = self._reloj()
        self._reclamos: dict[int, datetime] = {}  # id del trabajo → cuándo vence su reclamo
        self._sin_trabajo_hasta: datetime | None = None

    def latido(self, version: str | None, ocupado: bool | None = None) -> None:
        """El nodo llamó. «ocupado»: reclamó un trabajo (True) o lo cerró (False)."""
        self._contacto, self._version_nodo = self._reloj(), version
        if ocupado is not None:
            vence = timedelta(seconds=config.VENCIMIENTO_RECLAMO_VIDEO_S)
            self._ocupado_hasta = self._contacto + vence if ocupado else None

    def estado_nodo(self) -> dict:
        """Mientras analiza (minutos) el nodo no llama: sigue en línea hasta que venza su
        reclamo. Si no, en línea es haber llamado hace NODO_VIDEO_EN_LINEA_S o menos."""
        ahora = self._reloj()
        if self._contacto is None:
            return {"ultimo_contacto": None, "segundos_sin_contacto": None, "version": None,
                    "analizando": False, "en_linea": False, "al_dia": None}
        segundos = int((ahora - self._contacto).total_seconds())
        analizando = self._ocupado_hasta is not None and ahora < self._ocupado_hasta
        return {"ultimo_contacto": self._contacto, "segundos_sin_contacto": segundos,
                "version": self._version_nodo, "analizando": analizando,
                "en_linea": analizando or segundos <= config.NODO_VIDEO_EN_LINEA_S,
                "al_dia": version_al_dia(self._version_nodo)}

    def autorizar_subida(self, codigo: str, clave: str | None) -> None:
        """Antes de leer el archivo: solo quien creó el reporte, a tiempo y una sola vez."""
        reporte = self._reportes.buscar_por_clave(clave) if clave else None
        if reporte is None or reporte.codigo != codigo:
            raise VideoRechazado(403, "Solo se puede adjuntar el video desde el teléfono que "
                                      "envió el reporte.")
        ventana = timedelta(minutes=config.VIDEO_VENTANA_SUBIDA_MINUTOS)
        if self._reloj() - reporte.creado_en > ventana:
            raise VideoRechazado(403, "Ya pasó el tiempo para adjuntar el video a este "
                                      "reporte.")
        if self._videos.de_reporte(codigo) is not None:
            raise VideoRechazado(409, "Este reporte ya tiene un video.")
        self._exigir_cupo()

    def _exigir_cupo(self) -> None:
        """#188: a lo sumo MAX_VIDEOS_PENDIENTES esperando (cuida el espacio de la base). Con
        el cupo lleno el reporte ya llegó y se atiende con la descripción."""
        if self._videos.contar_esperando() >= config.MAX_VIDEOS_PENDIENTES:
            raise VideoRechazado(503, "Hay muchos videos esperando análisis. Tu reporte ya "
                                      "llegó y se atiende con la descripción.")

    def registrar(self, codigo: str, ruta: str, tamano: int) -> TrabajoVideo:
        try:
            self._exigir_cupo()  # otra subida pudo llenar el cupo mientras llegaba esta
        except VideoRechazado:
            self._almacen.borrar(ruta)
            raise
        trabajo = self._videos.crear(codigo, ruta, tamano, self._reloj())
        if trabajo is None:  # otro envío del mismo reporte ganó la carrera
            self._almacen.borrar(ruta)
            raise VideoRechazado(409, "Este reporte ya tiene un video.")
        self._hay_trabajo_nuevo()
        return trabajo

    def de_reporte(self, codigo: str) -> TrabajoVideo | None:
        return self._videos.de_reporte(codigo)

    def reclamar(self) -> TrabajoVideo | None:
        ahora = self._reloj()
        if self._sin_trabajo_hasta is not None and ahora < self._sin_trabajo_hasta:
            return None  # #390: se sabe que no hay trabajos; la base sigue dormida
        dura = timedelta(seconds=config.VENCIMIENTO_RECLAMO_VIDEO_S)
        trabajo = self._videos.reclamar(ahora, ahora - dura)
        if trabajo is not None:
            self._reclamos[trabajo.id] = ahora + dura
            return trabajo
        self._reclamos = {i: v for i, v in self._reclamos.items() if v > ahora}
        # Tras un reinicio no se conocen los reclamos de antes: se espera lo que dura uno.
        vencen = [*self._reclamos.values(), *([self._inicio + dura]
                                              if ahora < self._inicio + dura else [])]
        self._sin_trabajo_hasta = min(vencen) if vencen else datetime.max.replace(tzinfo=UTC)
        return None

    def _hay_trabajo_nuevo(self) -> None:
        self._sin_trabajo_hasta = None

    def _enviado(self, id_: int) -> TrabajoVideo:
        trabajo = self._videos.buscar(id_)
        if trabajo is None:
            raise VideoRechazado(404, "Trabajo de video no encontrado.")
        if trabajo.estado != EstadoVideo.ENVIADO:
            raise VideoRechazado(409, f"El trabajo está «{trabajo.estado.value}».")
        return trabajo

    def _cerrar(self, trabajo: TrabajoVideo, estado: EstadoVideo, motivo: str | None) -> None:
        trabajo.estado, trabajo.motivo, trabajo.terminado_en = estado, motivo, self._reloj()
        self._videos.guardar(trabajo)
        self._reclamos.pop(trabajo.id, None)
        self._almacen.borrar(trabajo.ruta)  # RNF-08: el video nunca se guarda para siempre

    def ruta_para_descargar(self, id_: int) -> str:
        trabajo = self._enviado(id_)
        if not self._almacen.existe(trabajo.ruta):
            self._cerrar(trabajo, EstadoVideo.FALLIDO, "el video ya no está en el servidor "
                         "(se reinició); manda el texto")
            raise VideoRechazado(410, "El video ya no está disponible.")
        return trabajo.ruta

    def terminar(self, id_: int, resultado: ResultadoVideo) -> TrabajoVideo:
        trabajo = self._enviado(id_)
        trabajo.evidencias, trabajo.medidas = list(resultado.evidencias), dict(resultado.medidas)
        trabajo.version_modelo, trabajo.tira = resultado.version_modelo, resultado.tira
        if resultado.prioridad is None:
            self._cerrar(trabajo, EstadoVideo.NO_CONCLUYENTE,
                         resultado.motivo or "el video no muestra bien al animal")
            return trabajo
        trabajo.prioridad, trabajo.confianza = resultado.prioridad, resultado.confianza
        reporte = self._reportes.buscar(trabajo.codigo)
        if reporte is not None:
            trabajo.discrepancia = reporte.prioridad not in (None, resultado.prioridad)
            if reporte.estado not in DECIDIDOS:  # RN-16: lo decidido por una persona no cambia
                aplicar_video(reporte, Resultado(resultado.prioridad, resultado.confianza,
                                                 list(resultado.evidencias)))
                self._reportes.actualizar_triaje(reporte)
        self._cerrar(trabajo, EstadoVideo.TERMINADO, None)
        return trabajo

    def autorizar_vista(self, id_: int) -> None:
        """Antes de leer el archivo: la vista llega mientras el trabajo se está analizando."""
        if self._vistas is None:
            raise VideoRechazado(503, "La vista previa del video no está activada.")
        self._enviado(id_)

    def registrar_vista(self, id_: int, ruta: str, tamano: int) -> None:
        """Guarda la vista previa (#214, cambia RNF-08). Una vista nueva reemplaza a la anterior."""
        try:
            trabajo = self._enviado(id_)
        except VideoRechazado:
            self._vistas.borrar(ruta)
            raise
        if trabajo.vista_ruta:
            self._vistas.borrar(trabajo.vista_ruta)
        trabajo.vista_ruta, trabajo.vista_bytes = ruta, tamano
        trabajo.vista_en = self._reloj()
        self._videos.guardar(trabajo)

    def vista_de(self, codigo: str) -> tuple[str, int] | None:
        trabajo = self._videos.de_reporte(codigo)
        if trabajo is None or not trabajo.vista_ruta or self._vistas is None:
            return None
        return trabajo.vista_ruta, trabajo.vista_bytes or 0

    def _reporte_cerrado(self, codigo: str) -> bool:
        reporte = self._reportes.buscar(codigo)
        descartado = reporte is not None and reporte.estado == EstadoReporte.DESCARTADO
        return descartado or self._rescate_atendido(codigo)

    def _limpiar_vistas(self) -> None:
        """La vista se borra a los VISTA_VIDEO_DIAS o cuando el reporte se cierra."""
        if self._vistas is None:
            return
        limite = self._reloj() - timedelta(days=config.VISTA_VIDEO_DIAS)
        self._vistas.purgar_antes_de(limite)  # huérfanas de subidas cortadas
        for trabajo in self._videos.con_vista():
            if trabajo.vista_en < limite or self._reporte_cerrado(trabajo.codigo):
                self._vistas.borrar(trabajo.vista_ruta)
                trabajo.vista_ruta = trabajo.vista_bytes = trabajo.vista_en = None
                self._videos.guardar(trabajo)

    def fallar(self, id_: int, motivo: str) -> TrabajoVideo:
        """El trabajador no pudo analizarlo: se reintenta; al agotar los intentos, fallido."""
        trabajo = self._enviado(id_)
        trabajo.intentos += 1
        if trabajo.intentos >= config.MAX_INTENTOS_VIDEO:
            self._cerrar(trabajo, EstadoVideo.FALLIDO, motivo[:300])
        else:
            trabajo.estado, trabajo.reclamado_en, trabajo.motivo = (
                EstadoVideo.PENDIENTE, None, motivo[:300])
            self._videos.guardar(trabajo)
            self._reclamos.pop(trabajo.id, None)
            self._hay_trabajo_nuevo()  # vuelve a la cola
        return trabajo

    def revisar(self) -> int:
        """Periódico: lo que nadie analizó en VIDEO_MAX_ESPERA_HORAS se da por fallido (el
        trabajador local estuvo apagado) y su video se borra."""
        limite = self._reloj() - timedelta(hours=config.VIDEO_MAX_ESPERA_HORAS)
        vencidos = self._videos.esperando_desde_antes(limite)
        self._almacen.purgar_antes_de(limite)  # huérfanos de subidas cortadas
        self._limpiar_vistas()
        for trabajo in vencidos:
            self._cerrar(trabajo, EstadoVideo.FALLIDO, "nadie lo analizó a tiempo; manda el "
                         "texto")
        self._limpiar_vistas()  # después de cerrar: no pisar con copias viejas
        return len(vencidos)

    def revisar_y_proxima(self) -> float | None:
        """#390: revisa y dice en cuántos segundos el video en espera más antiguo cumple
        VIDEO_MAX_ESPERA_HORAS; None si ninguno espera (la tarea duerme hasta una subida)."""
        self.revisar()
        ahora = self._reloj()
        # Creados antes de «ahora + 1 s» = todos los que esperan (pendientes o enviados).
        esperando = self._videos.esperando_desde_antes(ahora + timedelta(seconds=1))
        if not esperando:
            return None
        vence = min(t.creado_en for t in esperando) + timedelta(
            hours=config.VIDEO_MAX_ESPERA_HORAS)
        return max(1.0, (vence - ahora).total_seconds())
