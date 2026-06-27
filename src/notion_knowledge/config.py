"""Carga de configuracion: credenciales (.env) y bases de datos (default.toml).

Reutiliza el patron de notion-cycles-review. Lo que cambia: en vez de ciclos/
proyectos, aqui se configuran las *bases de datos de conocimiento* (wiki, actas,
tickets) a leer, cada una con su id de Notion y su tipo.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

# Tipos de fuente de conocimiento soportados.
KNOWLEDGE_KINDS = ("wiki", "meeting", "ticket", "note")


@dataclass
class DatabaseConfig:
    key: str                      # nombre logico, p. ej. "wiki"
    database_id: str              # id de la base de datos en Notion
    kind: str = "wiki"            # wiki | meeting | ticket
    title_property: str = "Name"  # propiedad que actua como titulo


def load_token() -> str:
    """Carga NOTION_TOKEN desde config/.env o el entorno. Lanza si falta."""
    env_path = CONFIG_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise RuntimeError(
            "Falta NOTION_TOKEN. Definelo en config/.env o como variable de entorno "
            "(ver config/.env.example)."
        )
    return token


@dataclass
class Config:
    cache_dir: Path = field(default_factory=lambda: Path("data/raw"))
    export_dir: Path = field(default_factory=lambda: Path("data/export"))
    databases: dict[str, DatabaseConfig] = field(default_factory=dict)
    name_aliases: dict[str, list[str]] = field(default_factory=dict)

    def database(self, key: str) -> DatabaseConfig | None:
        return self.databases.get(key)

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        cfg = cls()
        default_toml = CONFIG_DIR / "default.toml"
        if default_toml.exists():
            with open(default_toml, "rb") as f:
                data = tomllib.load(f)
            settings = data.get("settings", {})
            cfg.cache_dir = Path(settings.get("cache_dir", cfg.cache_dir))
            cfg.export_dir = Path(settings.get("export_dir", cfg.export_dir))
            for key, spec in data.get("databases", {}).items():
                if isinstance(spec, dict):
                    cfg.databases[key] = DatabaseConfig(
                        key=key,
                        database_id=str(spec.get("id", "")),
                        kind=spec.get("type", "wiki"),
                        title_property=spec.get("title_property", "Name"),
                    )

        names_toml = CONFIG_DIR / "names.toml"
        if names_toml.exists():
            with open(names_toml, "rb") as f:
                data = tomllib.load(f)
            cfg.name_aliases = data.get("aliases", {})

        if config_path and config_path.exists():
            with open(config_path, "rb") as f:
                extra = tomllib.load(f)
            for key, spec in extra.get("databases", {}).items():
                if isinstance(spec, dict):
                    cfg.databases[key] = DatabaseConfig(
                        key=key,
                        database_id=str(spec.get("id", "")),
                        kind=spec.get("type", "wiki"),
                        title_property=spec.get("title_property", "Name"),
                    )
        return cfg
