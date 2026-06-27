"""Modelos de dominio para notion-knowledge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeItem:
    """Una pieza de conocimiento (pagina wiki, acta de reunion o ticket)."""

    id: str                       # id de pagina de Notion
    source: str                   # clave de la base de datos (p. ej. "wiki")
    kind: str                     # wiki | meeting | ticket
    title: str
    url: str = ""
    created_time: str = ""
    last_edited_time: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    text: str = ""                # cuerpo (bloques aplanados)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "kind": self.kind,
            "title": self.title,
            "url": self.url,
            "created_time": self.created_time,
            "last_edited_time": self.last_edited_time,
            "properties": self.properties,
            "text": self.text,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KnowledgeItem:
        return cls(
            id=d["id"],
            source=d.get("source", ""),
            kind=d.get("kind", "wiki"),
            title=d.get("title", ""),
            url=d.get("url", ""),
            created_time=d.get("created_time", ""),
            last_edited_time=d.get("last_edited_time", ""),
            properties=d.get("properties", {}),
            text=d.get("text", ""),
            tags=d.get("tags", []),
        )

    def searchable_text(self) -> str:
        parts = [self.title, self.text]
        for v in self.properties.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(x) for x in v)
        return "\n".join(p for p in parts if p)
