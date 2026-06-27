"""Extraccion de texto plano desde estructuras de Notion (propiedades y bloques)."""

from __future__ import annotations

from typing import Any


def rich_text_to_plain(rich: list[dict[str, Any]] | None) -> str:
    if not rich:
        return ""
    return "".join(part.get("plain_text", "") for part in rich)


def property_to_value(prop: dict[str, Any]) -> Any:
    """Convierte un valor de propiedad de Notion a un valor Python simple."""
    ptype = prop.get("type")
    if ptype in ("title", "rich_text"):
        return rich_text_to_plain(prop.get(ptype))
    if ptype == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if ptype == "multi_select":
        return [s.get("name") for s in prop.get("multi_select", [])]
    if ptype == "status":
        st = prop.get("status")
        return st.get("name") if st else None
    if ptype == "people":
        return [p.get("name") or p.get("id") for p in prop.get("people", [])]
    if ptype == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    if ptype == "checkbox":
        return prop.get("checkbox")
    if ptype == "number":
        return prop.get("number")
    if ptype == "url":
        return prop.get("url")
    if ptype in ("created_time", "last_edited_time"):
        return prop.get(ptype)
    if ptype == "relation":
        return [r.get("id") for r in prop.get("relation", [])]
    if ptype == "formula":
        f = prop.get("formula", {})
        return f.get(f.get("type"))
    return None


def properties_to_dict(properties: dict[str, Any]) -> dict[str, Any]:
    return {name: property_to_value(prop) for name, prop in (properties or {}).items()}


# Tipos de bloque con texto en `rich_text` bajo su propia clave.
_TEXT_BLOCKS = (
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item", "quote", "callout", "toggle",
    "to_do",
)


def block_to_text(block: dict[str, Any]) -> str:
    btype = block.get("type", "")
    data = block.get(btype, {})
    if btype in _TEXT_BLOCKS:
        text = rich_text_to_plain(data.get("rich_text"))
        prefix = {
            "heading_1": "# ", "heading_2": "## ", "heading_3": "### ",
            "bulleted_list_item": "- ", "numbered_list_item": "1. ",
            "quote": "> ", "to_do": "[ ] ",
        }.get(btype, "")
        return (prefix + text) if text else ""
    if btype == "code":
        return rich_text_to_plain(data.get("rich_text"))
    if btype == "child_page":
        return data.get("title", "")
    return ""


def blocks_to_text(blocks: list[dict[str, Any]] | None) -> str:
    """Aplana bloques (con hijos recursivos en `_children`) a texto/markdown."""
    if not blocks:
        return ""
    lines: list[str] = []
    for block in blocks:
        line = block_to_text(block)
        if line:
            lines.append(line)
        children = block.get("_children")
        if children:
            child_text = blocks_to_text(children)
            if child_text:
                lines.append("\n".join("  " + l for l in child_text.splitlines()))
    return "\n".join(lines)
