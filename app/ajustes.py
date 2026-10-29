"""Ajustes de infraestructura leídos del entorno o del archivo .env (DT-01, DT-02).

Las reglas de negocio siguen en app/config.py; aquí van la conexión a PostgreSQL y la
clave de firma de los tokens.
"""
from __future__ import annotations

from urllib.parse import quote

from pydantic import SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_CARACTERES_SECRETO_JWT = 32


class ConfiguracionIncompleta(RuntimeError):
    pass


class AjustesBD(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    # SecretStr evita que la contraseña aparezca al imprimir los ajustes o en los logs.
    password: SecretStr
    db: str = "patitas"
    db_pruebas: str = "patitas_test"

    def url(self, pruebas: bool = False) -> str:
        """URL de SQLAlchemy; escapa la contraseña por si trae caracteres como @ o /."""
        base = self.db_pruebas if pruebas else self.db
        clave = quote(self.password.get_secret_value(), safe="")
        return f"postgresql+psycopg://{self.user}:{clave}@{self.host}:{self.port}/{base}"


class AjustesSeguridad(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PATITAS_", extra="ignore")

    jwt_secreto: SecretStr
    jwt_minutos: int = 30

    @field_validator("jwt_secreto")
    @classmethod
    def _secreto_largo(cls, valor: SecretStr) -> SecretStr:
        if len(valor.get_secret_value()) < MIN_CARACTERES_SECRETO_JWT:
            raise ValueError(f"mínimo {MIN_CARACTERES_SECRETO_JWT} caracteres")
        return valor

    @field_validator("jwt_minutos")
    @classmethod
    def _minutos_razonables(cls, valor: int) -> int:
        if not 1 <= valor <= 480:
            raise ValueError("entre 1 y 480 minutos")
        return valor


class AjustesCorreo(BaseSettings):
    """Servidor SMTP de las notificaciones (DT-03). Sin PATITAS_SMTP_HOST se usa el log."""

    model_config = SettingsConfigDict(env_prefix="PATITAS_", extra="ignore")

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_usuario: str | None = None
    smtp_contrasena: SecretStr | None = None
    smtp_remitente: str | None = None
    smtp_starttls: bool = True
    correos_coordinadores: str = ""  # separados por comas

    @field_validator("smtp_host", "smtp_usuario", "smtp_contrasena", "smtp_remitente",
                     mode="before")
    @classmethod
    def _vacio_es_ninguno(cls, valor):
        return None if isinstance(valor, str) and not valor.strip() else valor

    def coordinadores(self) -> list[str]:
        return [c.strip() for c in self.correos_coordinadores.split(",") if c.strip()]


class AjustesAdmin(BaseSettings):
    """Primera cuenta de administración (#67). Vacías = no se crea ninguna."""

    model_config = SettingsConfigDict(env_prefix="PATITAS_ADMIN_", extra="ignore")

    correo: str | None = None
    contrasena: SecretStr | None = None
    nombre: str = "Administración"

    @field_validator("correo", "contrasena", mode="before")
    @classmethod
    def _vacio_es_ninguno(cls, valor):
        return None if isinstance(valor, str) and not valor.strip() else valor


class AjustesDemo(BaseSettings):
    """Datos de demostración (#109). Desactivados salvo PATITAS_DEMO_ACTIVA=true."""

    model_config = SettingsConfigDict(env_prefix="PATITAS_DEMO_", extra="ignore")

    activa: bool = False
    contrasena: SecretStr | None = None

    @field_validator("contrasena", mode="before")
    @classmethod
    def _vacio_es_ninguno(cls, valor):
        return None if isinstance(valor, str) and not valor.strip() else valor

    def contrasena_si_activa(self) -> str | None:
        if not self.activa or self.contrasena is None:
            return None
        return self.contrasena.get_secret_value()


def _cargar(clase, prefijo: str, archivo_env: str | None):
    try:
        return clase(_env_file=archivo_env)
    except ValidationError as error:
        faltantes = ", ".join(f"{prefijo}{e['loc'][0]}".upper() for e in error.errors())
        raise ConfiguracionIncompleta(
            f"Falta o es inválido {faltantes}: copia .env.example como .env y complétalo."
        ) from error


def cargar_ajustes(archivo_env: str | None = ".env") -> AjustesBD:
    return _cargar(AjustesBD, "POSTGRES_", archivo_env)


def cargar_ajustes_seguridad(archivo_env: str | None = ".env") -> AjustesSeguridad:
    return _cargar(AjustesSeguridad, "PATITAS_", archivo_env)


def cargar_ajustes_correo(archivo_env: str | None = ".env") -> AjustesCorreo:
    return _cargar(AjustesCorreo, "PATITAS_", archivo_env)


def cargar_ajustes_admin(archivo_env: str | None = ".env") -> AjustesAdmin:
    return _cargar(AjustesAdmin, "PATITAS_ADMIN_", archivo_env)


def cargar_ajustes_demo(archivo_env: str | None = ".env") -> AjustesDemo:
    return _cargar(AjustesDemo, "PATITAS_DEMO_", archivo_env)
