"""Cache local de items de conocimiento (data/raw/<source>/<page_id>.json)."""

from __future__ import annotations

import json
from pathlib import Path

from notion_knowledge.models import KnowledgeItem


class KnowledgeStore:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)

    def _source_dir(self, source: str) -> Path:
        return self.cache_dir / source

    def save_item(self, item: KnowledgeItem) -> Path:
        d = self._source_dir(item.source)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{item.id}.json"
        path.write_text(
            json.dumps(item.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    def list_sources(self) -> list[str]:
        if not self.cache_dir.exists():
            return []
        return sorted(p.name for p in self.cache_dir.iterdir() if p.is_dir())

    def load_items(self, source: str | None = None) -> list[KnowledgeItem]:
        items: list[KnowledgeItem] = []
        sources = [source] if source else self.list_sources()
        for src in sources:
            d = self._source_dir(src)
            if not d.exists():
                continue
            for path in sorted(d.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    items.append(KnowledgeItem.from_dict(data))
                except (json.JSONDecodeError, KeyError):
                    continue
        return items

    def get_item(self, item_id: str) -> KnowledgeItem | None:
        for item in self.load_items():
            if item.id == item_id:
                return item
        return None

    def counts(self) -> dict[str, int]:
        return {src: len(self.load_items(src)) for src in self.list_sources()}
