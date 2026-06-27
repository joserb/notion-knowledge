"""Exporta items de conocimiento a Markdown (compatible Obsidian) en data/export."""

from __future__ import annotations

import re
from pathlib import Path

from notion_knowledge.models import KnowledgeItem


def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80] or "sin-titulo"


def item_to_markdown(item: KnowledgeItem) -> str:
    fm = ["---", f'title: "{item.title}"', f"source: {item.source}", f"kind: {item.kind}"]
    if item.url:
        fm.append(f"url: {item.url}")
    if item.created_time:
        fm.append(f"created: {item.created_time}")
    if item.last_edited_time:
        fm.append(f"updated: {item.last_edited_time}")
    if item.tags:
        fm.append("tags: [" + ", ".join(item.tags) + "]")
    fm.append("---")
    body = item.text or "_(sin contenido)_"
    return "\n".join(fm) + f"\n\n# {item.title}\n\n{body}\n"


def export_items(items: list[KnowledgeItem], export_dir: Path) -> list[Path]:
    written: list[Path] = []
    for item in items:
        d = Path(export_dir) / item.source
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{_slug(item.title)}-{item.id[:8]}.md"
        path.write_text(item_to_markdown(item), encoding="utf-8")
        written.append(path)
    return written
