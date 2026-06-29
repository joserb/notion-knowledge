"""Exporta entity cards al twave-knowledge-atlas.

Genera un fichero JSONL (una EntityCard por línea) conforme a
``twave-knowledge-atlas/schemas/entity_card.schema.json`` a partir de la caché local
de conocimiento (``data/raw``), sin acceso en vivo a Notion.

El atlas lo ingiere con::

    atlas import <ruta>/entity_cards.jsonl

Uso::

    uv run python -m notion_knowledge.atlas_export
    uv run python -m notion_knowledge.atlas_export --source tickets
    uv run python -m notion_knowledge.atlas_export --out ruta.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

GATEWAY = "notion-knowledge"
DEFAULT_EXPORT = Path("data/exports/entity_cards.jsonl")

# kind del item -> tipo de entidad del catálogo común del hub.
# (El hub no contempla "meeting"/"topic"; las actas se modelan como document y se
#  conserva el matiz en source_type.)
_KIND_TO_TYPE = {"ticket": "ticket"}


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _entity_type(kind: str) -> str:
    return _KIND_TO_TYPE.get(kind, "document")


def _summary(text: str, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def _meeting_date(item: Any) -> str:
    """Fecha real de la reunión (propiedad ``Fecha`` de Notion); si falta, la de
    creación. Devuelve solo la parte ``YYYY-MM-DD``."""
    props = getattr(item, "properties", None) or {}
    fecha = props.get("Fecha")
    if isinstance(fecha, str) and fecha.strip():
        return fecha.strip()[:10]
    return (getattr(item, "created_time", "") or "")[:10]


def _canonical_name(item: Any) -> str:
    """Nombre canónico de la card.

    Las reuniones recurrentes comparten título (p. ej. la "Reunión de producción"
    semanal). Como el atlas fusiona entidades que comparten un alias y el nombre
    canónico actúa como alias, sin desambiguar todas las instancias colapsarían en
    una sola entidad y se perdería el histórico. Cualificamos el nombre de cada
    acta con su fecha para que cada reunión sea una entidad propia.
    """
    title = item.title or item.id
    if getattr(item, "kind", "") == "meeting":
        date = _meeting_date(item)
        if date:
            return f"{title} ({date})"
    return title


def card_for_item(item: Any) -> dict[str, Any]:
    """Construye una EntityCard a partir de un KnowledgeItem. Sin IO."""
    etype = _entity_type(getattr(item, "kind", ""))
    page_id = item.id
    source_ref: dict[str, Any] = {
        "gateway": GATEWAY,
        "source_id": f"page:{page_id}",
        "source_type": getattr(item, "kind", "") or "document",
        "title": item.title,
    }
    if getattr(item, "url", ""):
        source_ref["url"] = item.url
    if getattr(item, "last_edited_time", ""):
        source_ref["last_seen"] = item.last_edited_time

    best_tools = {"internal_context": "notion_knowledge.search"}
    if etype == "ticket":
        best_tools["ticket_detail"] = "notion_knowledge.get_document"
    else:
        best_tools["document_detail"] = "notion_knowledge.get_document"

    return {
        "id": f"{etype}:{page_id}",
        "type": etype,
        "canonical_name": _canonical_name(item),
        "aliases": [],
        "summary": _summary(getattr(item, "text", "")),
        "known_in": [GATEWAY],
        "best_tools": best_tools,
        "source_refs": [source_ref],
        "relations": [],
        "last_seen": getattr(item, "last_edited_time", "") or _today(),
        "last_updated": _today(),
        "confidence": "medium",
        "staleness": "fresh",
        "warnings": [],
    }


def _is_exportable(item: Any) -> bool:
    """Una card necesita un título usable para tener identidad propia. Los items
    sin título (p. ej. una página de reunión creada en blanco) producirían una
    card con el page-id crudo como nombre y sin contenido, así que se omiten."""
    return bool((getattr(item, "title", "") or "").strip())


def build_all(items: list[Any]) -> list[dict[str, Any]]:
    """Construye las cards para una lista de KnowledgeItem. Sin IO.

    Omite los items sin título usable (ver ``_is_exportable``)."""
    return [card_for_item(item) for item in items if _is_exportable(item)]


def _load_items(source: str | None = None) -> list[Any]:
    from notion_knowledge.config import Config
    from notion_knowledge.store import KnowledgeStore

    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    return store.load_items(source)


def write_jsonl(cards: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for card in cards:
            fh.write(json.dumps(card, ensure_ascii=False) + "\n")
    return output_path


def export(
    output_path: Path | None = None, source: str | None = None
) -> tuple[Path, int, int]:
    """Exporta las cards. Devuelve (ruta, nº exportadas, nº items omitidos)."""
    items = _load_items(source)
    cards = build_all(items)
    out = write_jsonl(cards, Path(output_path) if output_path else DEFAULT_EXPORT)
    return out, len(cards), len(items) - len(cards)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="notion_knowledge.atlas_export",
        description="Exporta entity cards de conocimiento al twave-knowledge-atlas.",
    )
    parser.add_argument("--out", type=Path, default=None, help=f"Salida JSONL (def. {DEFAULT_EXPORT})")
    parser.add_argument("--source", default=None, help="Filtra por fuente (p. ej. wiki, meetings, tickets)")
    args = parser.parse_args(argv)
    out, count, skipped = export(output_path=args.out, source=args.source)
    msg = f"Exportadas {count} entity cards a {out}"
    if skipped:
        msg += f" ({skipped} item(s) sin título omitidos)"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
