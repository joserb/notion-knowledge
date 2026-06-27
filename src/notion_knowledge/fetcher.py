"""Descarga bases de datos de Notion a la cache local como KnowledgeItem."""

from __future__ import annotations

from notion_knowledge.config import Config, DatabaseConfig
from notion_knowledge.models import KnowledgeItem
from notion_knowledge.notion_client import RateLimitedNotionClient
from notion_knowledge.notion_text import blocks_to_text, properties_to_dict, rich_text_to_plain
from notion_knowledge.store import KnowledgeStore


class KnowledgeFetcher:
    def __init__(self, client: RateLimitedNotionClient, config: Config):
        self.client = client
        self.config = config
        self.store = KnowledgeStore(config.cache_dir)

    def _title(self, page: dict, db: DatabaseConfig) -> str:
        props = page.get("properties", {})
        # Propiedad configurada
        prop = props.get(db.title_property)
        if prop and prop.get("type") == "title":
            return rich_text_to_plain(prop.get("title"))
        # Cualquier propiedad de tipo title
        for p in props.values():
            if p.get("type") == "title":
                return rich_text_to_plain(p.get("title"))
        return "(sin titulo)"

    def fetch_database(self, key: str, *, with_body: bool = True) -> int:
        """Descarga una base de datos configurada. Devuelve nº de items."""
        db = self.config.database(key)
        if db is None:
            raise ValueError(f"Base de datos no configurada: {key}")
        pages = self.client.query_database(db.database_id)
        count = 0
        for page in pages:
            page_id = page.get("id", "")
            props = properties_to_dict(page.get("properties", {}))
            text = ""
            if with_body:
                blocks = self.client.get_all_blocks_recursive(page_id)
                text = blocks_to_text(blocks)
            tags = props.get("Tags") or props.get("Etiquetas") or []
            if isinstance(tags, str):
                tags = [tags]
            item = KnowledgeItem(
                id=page_id,
                source=key,
                kind=db.kind,
                title=self._title(page, db),
                url=page.get("url", ""),
                created_time=page.get("created_time", ""),
                last_edited_time=page.get("last_edited_time", ""),
                properties=props,
                text=text,
                tags=[t for t in tags if isinstance(t, str)],
            )
            self.store.save_item(item)
            count += 1
        return count

    def fetch_all(self, *, with_body: bool = True) -> dict[str, int]:
        return {
            k: self.fetch_database(k, with_body=with_body)
            for k, db in self.config.databases.items()
            if db.database_id
        }
