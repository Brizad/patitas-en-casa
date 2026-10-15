"""Tablas de PostgreSQL (DT-01). Cada cambio aquí necesita una migración en migraciones/."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.dominio.modelos import (
    Especie,
    EstadoReporte,
    EstadoRescate,
    Prioridad,
    ResultadoRescate,
    Rol,
)


def _valores(enum) -> str:
    return ", ".join(f"'{miembro.value}'" for miembro in enum)


metadata = MetaData()

reportes = Table(
    "reportes",
    metadata,
    Column("codigo", String(8), primary_key=True),
    Column("descripcion", Text, nullable=False),
    Column("latitud", Double),
    Column("longitud", Double),
    Column("direccion", Text),
    Column("video_segundos", Integer),
    Column("estado", String(20), nullable=False),
    Column("prioridad", String(10)),
    Column("confianza", Double),
    Column("evidencias", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("creado_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"estado IN ({_valores(EstadoReporte)})", name="ck_reportes_estado"),
    CheckConstraint(f"prioridad IN ({_valores(Prioridad)})", name="ck_reportes_prioridad"),
    CheckConstraint("confianza BETWEEN 0 AND 1", name="ck_reportes_confianza"),
    CheckConstraint("video_segundos >= 0", name="ck_reportes_video"),
    # RN-01: GPS completo o dirección escrita.
    CheckConstraint(
        "(latitud IS NOT NULL AND longitud IS NOT NULL) OR direccion IS NOT NULL",
        name="ck_reportes_ubicacion",
    ),
)

# DT-05: la ocupación vive en la base; el cupo se toma con un UPDATE condicional (RN-04).
refugios = Table(
    "refugios",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nombre", Text, nullable=False),
    Column("capacidad", Integer, nullable=False),
    Column("ocupados", Integer, nullable=False, server_default=text("0")),
    CheckConstraint("capacidad > 0", name="ck_refugios_capacidad"),
    CheckConstraint("ocupados BETWEEN 0 AND capacidad", name="ck_refugios_ocupados"),
)

animales = Table(
    "animales",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("refugio_id", Integer, ForeignKey("refugios.id"), nullable=False),
    Column("nombre", Text, nullable=False),
    Column("especie", String(10), nullable=False),
    Column("estado_salud", Text, nullable=False),
    Column("vacunado", Boolean, nullable=False, server_default=false()),
    Column("esterilizado", Boolean, nullable=False, server_default=false()),
    Column("ingresado_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(f"especie IN ({_valores(Especie)})", name="ck_animales_especie"),
)

# DT-02: cuentas del personal. Solo se guarda el hash Argon2id de la contraseña.
usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("correo", Text, nullable=False),
    Column("nombre", Text, nullable=False),
    Column("rol", String(20), nullable=False),
    Column("hash_contrasena", Text, nullable=False),
    Column("activo", Boolean, nullable=False, server_default=true()),
    Column("creado_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("correo", name="uq_usuarios_correo"),
    CheckConstraint("correo = lower(correo)", name="ck_usuarios_correo_minusculas"),
    CheckConstraint(f"rol IN ({_valores(Rol)})", name="ck_usuarios_rol"),
)

# DT-06: un fallo de inicio de sesión por fila. clave = "correo:<correo>" o "ip:<ip>".
intentos_fallidos = Table(
    "intentos_fallidos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("clave", Text, nullable=False),
    Column("ocurrido_en", DateTime(timezone=True), nullable=False),
    CheckConstraint("clave <> ''", name="ck_intentos_fallidos_clave"),
    Index("ix_intentos_fallidos_clave_ocurrido_en", "clave", "ocurrido_en"),
)

# HU-02: bitácora de confirmaciones y ajustes de prioridad (RN-06, RN-16).
decisiones_triaje = Table(
    "decisiones_triaje",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("reporte_codigo", String(8), ForeignKey("reportes.codigo"), nullable=False),
    Column("veterinario", Text, nullable=False),
    Column("prioridad_sugerida", String(10), nullable=False),
    Column("prioridad_final", String(10), nullable=False),
    Column("justificacion", Text),
    Column("decidido_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(f"prioridad_sugerida IN ({_valores(Prioridad)})",
                    name="ck_decisiones_prioridad_sugerida"),
    CheckConstraint(f"prioridad_final IN ({_valores(Prioridad)})",
                    name="ck_decisiones_prioridad_final"),
    # RN-16 también en la base: cambiar la prioridad exige justificación de 10+ caracteres.
    # El IS NOT NULL importa: un CHECK que da NULL deja pasar la fila.
    CheckConstraint("prioridad_final = prioridad_sugerida OR (justificacion IS NOT NULL "
                    "AND char_length(btrim(justificacion)) >= 10)",
                    name="ck_decisiones_justificacion"),
    UniqueConstraint("reporte_codigo", name="uq_decisiones_reporte"),
)

# HU-06: disponibilidad de los rescatistas (RF-15) y rescates (RN-08).
rescatistas = Table(
    "rescatistas",
    metadata,
    Column("correo", Text, primary_key=True),
    Column("disponible", Boolean, nullable=False, server_default=false()),
    Column("actualizado_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

rescates = Table(
    "rescates",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("reporte_codigo", String(8), ForeignKey("reportes.codigo"), nullable=False),
    Column("rescatista", Text, nullable=False),
    Column("estado", String(12), nullable=False),
    Column("resultado", String(20)),
    Column("aceptado_en", DateTime(timezone=True), nullable=False),
    Column("actualizado_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"estado IN ({_valores(EstadoRescate)})", name="ck_rescates_estado"),
    CheckConstraint(f"resultado IN ({_valores(ResultadoRescate)})",
                    name="ck_rescates_resultado"),
    # Hay resultado si y solo si el rescate se atendió.
    CheckConstraint("(estado = 'atendido') = (resultado IS NOT NULL)",
                    name="ck_rescates_resultado_al_atender"),
)

# RN-08 en la base: un rescate vigente por reporte y un rescate activo por rescatista.
Index("uq_rescates_reporte_vigente", rescates.c.reporte_codigo, unique=True,
      postgresql_where=text("estado <> 'liberado'"))
Index("uq_rescates_rescatista_activo", rescates.c.rescatista, unique=True,
      postgresql_where=text("estado IN ('en_camino', 'en_sitio')"))
