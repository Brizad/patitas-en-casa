"""Observabilidad (FPI-29): trazas y métricas con OpenTelemetry y registros en JSON.

Se activa con PATITAS_OBSERVABILIDAD=1. Nunca registra datos personales: ni descripción,
ni coordenadas, ni dirección, ni contacto (Ley 1581 de 2012, RN-14).
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

CAMPOS_PROHIBIDOS = {"descripcion", "direccion", "latitud", "longitud", "contacto",
                     "correo", "clave", "contrasena", "token", "cedula"}
BORDES_MS = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]

tracer = trace.get_tracer("patitas")
log = logging.getLogger("patitas.eventos")


class FormatoJSON(logging.Formatter):
    """Una línea JSON por evento, con la traza para correlacionar log ↔ span."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = trace.get_current_span().get_span_context()
        datos = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"), "nivel": record.levelname,
                 "evento": record.getMessage(),
                 "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else None}
        extra = getattr(record, "datos", {})
        datos.update({k: v for k, v in extra.items() if k not in CAMPOS_PROHIBIDOS})
        return json.dumps(datos, ensure_ascii=False)


def _configurar() -> None:
    recurso = Resource.create({"service.name": "patitas-en-casa",
                               "deployment.environment": os.getenv("PATITAS_ENTORNO", "local")})
    muestreo = float(os.getenv("PATITAS_OTEL_MUESTREO", "0.1"))   # 10 % de las trazas
    proveedor = TracerProvider(resource=recurso, sampler=ParentBased(TraceIdRatioBased(muestreo)))
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        proveedor.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    elif os.getenv("PATITAS_OTEL_CONSOLA") == "1":
        proveedor.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(proveedor)
    vista = View(instrument_name="http.server.duration",
                 aggregation=ExplicitBucketHistogramAggregation(BORDES_MS))
    metrics.set_meter_provider(MeterProvider(resource=recurso, views=[vista],
                                             metric_readers=[PrometheusMetricReader()]))
    manejador = logging.StreamHandler()
    manejador.setFormatter(FormatoJSON())
    log.handlers[:] = [manejador]
    log.setLevel(logging.INFO)
    log.propagate = False


def instrumentar(app: FastAPI) -> None:
    if os.getenv("PATITAS_OBSERVABILIDAD") != "1":
        return
    _configurar()
    medidor = metrics.get_meter("patitas")
    duracion = medidor.create_histogram("http.server.duration", unit="ms",
                                        description="Latencia de las peticiones HTTP")
    peticiones = medidor.create_counter("http.server.requests",
                                        description="Peticiones HTTP por ruta y estado")
    token_metricas = os.getenv("PATITAS_METRICAS_TOKEN", "")

    @app.middleware("http")
    async def medir(request: Request, call_next):
        inicio = time.perf_counter()
        with tracer.start_as_current_span(f"{request.method} {request.url.path}",
                                          kind=trace.SpanKind.SERVER) as span:
            respuesta = await call_next(request)
            # Plantilla de la ruta (/reportes/{codigo}), nunca el código real: baja cardinalidad.
            ruta = getattr(request.scope.get("route"), "path", "sin_ruta")
            span.update_name(f"{request.method} {ruta}")
            span.set_attribute("http.route", ruta)
            span.set_attribute("http.response.status_code", respuesta.status_code)
        ms = (time.perf_counter() - inicio) * 1000
        etiquetas = {"http.method": request.method, "http.route": ruta,
                     "http.status_class": f"{respuesta.status_code // 100}xx"}
        duracion.record(ms, etiquetas)
        peticiones.add(1, etiquetas)
        return respuesta

    @app.get("/metrics", include_in_schema=False)
    def exponer_metricas(request: Request):
        enviado = request.headers.get("authorization", "").removeprefix("Bearer ")
        if token_metricas and not secrets.compare_digest(enviado, token_metricas):
            return PlainTextResponse("No autorizado", status_code=401)
        return PlainTextResponse(generate_latest().decode(), media_type=CONTENT_TYPE_LATEST)


def evento(nombre: str, **datos) -> None:
    """Log estructurado; los campos con datos personales se descartan siempre."""
    log.info(nombre, extra={"datos": datos})
