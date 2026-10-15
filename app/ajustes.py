"""Ajustes de infraestructura leídos del entorno o del archivo .env (DT-01).

Las reglas de negocio siguen en app/config.py; aquí solo va la conexión a PostgreSQL.
"""
from __future__ import annotations

from urllib.parse import quote

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


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


def cargar_ajustes(archivo_env: str | None = ".env") -> AjustesBD:
    try:
        return AjustesBD(_env_file=archivo_env)
    except ValidationError as error:
        faltantes = ", ".join(f"POSTGRES_{e['loc'][0]}".upper() for e in error.errors())
        raise ConfiguracionIncompleta(
            f"Falta o es inválido {faltantes}: copia .env.example como .env y complétalo."
        ) from error
