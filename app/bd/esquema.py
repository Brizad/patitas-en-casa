"""Tablas de PostgreSQL (DT-01). Cada cambio aquí necesita una migración en migraciones/."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.adopciones.modelos import (
    Energia,
    EstadoPublicacion,
    EstadoSolicitud,
    Tamano,
    Vivienda,
)
from app.avisos.modelos import EstadoAviso
from app.dominio.modelos import (
    Especie,
    EstadoReporte,
    EstadoRescate,
    MotivoDescarte,
    MotivoEgreso,
    Prioridad,
    ResultadoRescate,
    Rol,
    TipoNota,
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
    Column("comuna", SmallInteger),  # HU-06: comuna de Cúcuta, opcional
    # RF-12 (#61): clave que genera la PWA; el reenvío con la misma clave no duplica.
    Column("clave_idempotencia", String(64), unique=True),
    Column("version_modelo", String(40)),  # RF-20 (#75)
    CheckConstraint(f"estado IN ({_valores(EstadoReporte)})", name="ck_reportes_estado"),
    CheckConstraint("comuna BETWEEN 1 AND 10", name="ck_reportes_comuna"),
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
    Column("direccion", Text),  # #108 (RF-14)
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
    # RF-26 (#75): fecha y motivo del egreso, juntos o ninguno.
    Column("egresado_en", DateTime(timezone=True)),
    Column("motivo_egreso", String(15)),
    CheckConstraint(f"especie IN ({_valores(Especie)})", name="ck_animales_especie"),
    CheckConstraint(f"motivo_egreso IN ({_valores(MotivoEgreso)})",
                    name="ck_animales_motivo_egreso"),
    CheckConstraint("(egresado_en IS NULL) = (motivo_egreso IS NULL)",
                    name="ck_animales_egreso_completo"),
)

# RF-24 (#75): historial clínico; las notas solo se insertan.
historial_clinico = Table(
    "historial_clinico",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("animal_id", Integer, ForeignKey("animales.id"), nullable=False),
    Column("autor", Text, nullable=False),
    Column("tipo", String(15), nullable=False),
    Column("texto", Text, nullable=False),
    Column("registrada_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"tipo IN ({_valores(TipoNota)})", name="ck_historial_tipo"),
    CheckConstraint("btrim(texto) <> ''", name="ck_historial_texto"),
    Index("ix_historial_clinico_animal", "animal_id"),
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
    Column("refugio_id", Integer, ForeignKey("refugios.id")),  # #67 (RF-14)
    UniqueConstraint("correo", name="uq_usuarios_correo"),
    CheckConstraint("correo = lower(correo)", name="ck_usuarios_correo_minusculas"),
    CheckConstraint(f"rol IN ({_valores(Rol)})", name="ck_usuarios_rol"),
)

# RF-08 (#85): perfil del adoptante, uno por cuenta. Datos mínimos (RNF-08, RNF-16).
perfiles_adoptante = Table(
    "perfiles_adoptante",
    metadata,
    Column("correo", Text, ForeignKey("usuarios.correo"), primary_key=True),
    Column("vivienda", String(12), nullable=False),
    Column("tiene_patio", Boolean, nullable=False),
    Column("hay_ninos", Boolean, nullable=False),
    Column("otros_animales", Boolean, nullable=False),
    Column("horas_solo_al_dia", SmallInteger, nullable=False),
    Column("experiencia", Boolean, nullable=False),
    Column("acepta_seguimiento", Boolean, nullable=False),
    Column("actualizado_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"vivienda IN ({_valores(Vivienda)})", name="ck_perfiles_vivienda"),
    CheckConstraint("horas_solo_al_dia BETWEEN 0 AND 24", name="ck_perfiles_horas"),
)

# RF-25 (#85): animales publicados para adopción; una publicación por animal.
publicaciones = Table(
    "publicaciones",
    metadata,
    Column("animal_id", Integer, ForeignKey("animales.id"), primary_key=True),
    Column("descripcion", Text, nullable=False),
    Column("tamano", String(10), nullable=False),
    Column("energia", String(10), nullable=False),
    Column("edad_meses", SmallInteger, nullable=False),
    Column("apto_ninos", Boolean, nullable=False),
    Column("apto_otros_animales", Boolean, nullable=False),
    Column("necesita_patio", Boolean, nullable=False),
    Column("estado", String(12), nullable=False),
    Column("publicado_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"tamano IN ({_valores(Tamano)})", name="ck_publicaciones_tamano"),
    CheckConstraint(f"energia IN ({_valores(Energia)})", name="ck_publicaciones_energia"),
    CheckConstraint(f"estado IN ({_valores(EstadoPublicacion)})",
                    name="ck_publicaciones_estado"),
    CheckConstraint("edad_meses BETWEEN 0 AND 360", name="ck_publicaciones_edad"),
)

# RF-27 (#85): solicitudes de adopción.
solicitudes = Table(
    "solicitudes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("animal_id", Integer, ForeignKey("publicaciones.animal_id"), nullable=False),
    Column("adoptante", Text, ForeignKey("usuarios.correo"), nullable=False),
    Column("mensaje", Text, nullable=False, server_default=""),
    Column("estado", String(10), nullable=False),
    Column("creada_en", DateTime(timezone=True), nullable=False),
    Column("decidida_por", Text),
    Column("decidida_en", DateTime(timezone=True)),
    Column("razon", Text),
    CheckConstraint(f"estado IN ({_valores(EstadoSolicitud)})", name="ck_solicitudes_estado"),
)
Index("uq_solicitudes_pendiente", solicitudes.c.animal_id, solicitudes.c.adoptante,
      unique=True, postgresql_where=text("estado = 'pendiente'"))
# RN-11: una sola adopción aprobada por animal, también con dos coordinadores a la vez.
Index("uq_solicitudes_aprobada", solicitudes.c.animal_id, unique=True,
      postgresql_where=text("estado = 'aprobada'"))

# RF-10 (#85): seguimientos a los 30, 90 y 180 días de la adopción.
seguimientos = Table(
    "seguimientos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("solicitud_id", Integer, ForeignKey("solicitudes.id"), nullable=False),
    Column("dia", SmallInteger, nullable=False),
    Column("programado_para", DateTime(timezone=True), nullable=False),
    Column("realizado_en", DateTime(timezone=True)),
    Column("nota", Text),
    Column("registrado_por", Text),
    CheckConstraint("dia IN (30, 90, 180)", name="ck_seguimientos_dia"),
    UniqueConstraint("solicitud_id", "dia", name="uq_seguimientos_dia"),
)

# RF-32 (#102): bitácora general. Solo INSERT: un disparador (migración 0020) rechaza
# UPDATE y DELETE.
bitacora = Table(
    "bitacora",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("momento", DateTime(timezone=True), nullable=False),
    Column("actor", Text, nullable=False),
    Column("accion", Text, nullable=False),
    Column("objeto", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("estado_http", SmallInteger, nullable=False),
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
    Column("version_modelo", String(40)),  # RF-20, D-04 (#75)
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

# D-02 (#75): bitácora de reportes descartados (uno por reporte).
descartes = Table(
    "descartes",
    metadata,
    Column("reporte_codigo", String(8), ForeignKey("reportes.codigo"), primary_key=True),
    Column("veterinario", Text, nullable=False),
    Column("motivo", String(10), nullable=False),
    Column("duplicado_de", String(8), ForeignKey("reportes.codigo")),
    Column("justificacion", Text, nullable=False),
    Column("descartado_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"motivo IN ({_valores(MotivoDescarte)})", name="ck_descartes_motivo"),
    CheckConstraint("char_length(btrim(justificacion)) >= 10",
                    name="ck_descartes_justificacion"),
)

# HU-06: disponibilidad de los rescatistas (RF-15) y rescates (RN-08).
rescatistas = Table(
    "rescatistas",
    metadata,
    Column("correo", Text, primary_key=True),
    Column("disponible", Boolean, nullable=False, server_default=false()),
    Column("actualizado_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # HU-06 (#46): comunas que cubre; vacío = toda la ciudad.
    Column("comunas", ARRAY(SmallInteger), nullable=False, server_default=text("'{}'")),
    CheckConstraint("comunas <@ ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]::smallint[]",
                    name="ck_rescatistas_comunas"),
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

# HU-06 (#46, RF-23): reportes escalados al coordinador por no tener rescatista a tiempo. La
# llave primaria garantiza un solo aviso aunque varios procesos revisen a la vez.
escalamientos = Table(
    "escalamientos",
    metadata,
    Column("reporte_codigo", String(8), ForeignKey("reportes.codigo"), primary_key=True),
    Column("escalado_en", DateTime(timezone=True), nullable=False),
)

# #63 (outbox, D-03): avisos a rescatistas guardados en la misma transacción que la confirmación
# y enviados después por el procesador de avisos.
avisos = Table(
    "avisos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("reporte_codigo", String(8), ForeignKey("reportes.codigo"), nullable=False),
    Column("destinatario", Text, nullable=False),
    Column("mensaje", Text, nullable=False),
    Column("estado", String(10), nullable=False),
    Column("intentos", Integer, nullable=False, server_default=text("0")),
    Column("ultimo_error", Text),
    Column("creado_en", DateTime(timezone=True), nullable=False),
    Column("proximo_intento_en", DateTime(timezone=True), nullable=False),
    Column("reclamado_en", DateTime(timezone=True)),
    Column("enviado_en", DateTime(timezone=True)),
    CheckConstraint(f"estado IN ({_valores(EstadoAviso)})", name="ck_avisos_estado"),
    CheckConstraint("intentos >= 0", name="ck_avisos_intentos"),
    # Un aviso por rescatista y reporte: repetir la confirmación no duplica avisos.
    UniqueConstraint("reporte_codigo", "destinatario", name="uq_avisos_reporte_destinatario"),
    Index("ix_avisos_estado_proximo_intento", "estado", "proximo_intento_en"),
)
