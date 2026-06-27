from pathlib import Path

from notion_knowledge.markdown_export import item_to_markdown, export_items
from notion_knowledge.models import KnowledgeItem
from notion_knowledge.store import KnowledgeStore


def _item():
    return KnowledgeItem(id="abc12345", source="wiki", kind="wiki",
                         title="Guia de despliegue", url="https://notion.so/abc",
                         text="Pasos para desplegar.", tags=["deploy"])


def test_store_roundtrip(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    store.save_item(_item())
    items = store.load_items()
    assert len(items) == 1 and items[0].title == "Guia de despliegue"
    assert store.counts() == {"wiki": 1}
    assert store.get_item("abc12345") is not None


def test_markdown_has_frontmatter_and_title():
    md = item_to_markdown(_item())
    assert md.startswith("---")
    assert 'title: "Guia de despliegue"' in md
    assert "# Guia de despliegue" in md
    assert "tags: [deploy]" in md


def test_export_writes_files(tmp_path: Path):
    written = export_items([_item()], tmp_path)
    assert len(written) == 1 and written[0].exists()
    assert written[0].suffix == ".md"
