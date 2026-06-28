"""Tests del export de entity cards al twave-knowledge-atlas (sin IO)."""

from __future__ import annotations

from types import SimpleNamespace

from notion_knowledge.atlas_export import build_all, card_for_item


def _item(**kw: object) -> SimpleNamespace:
    base = {
        "id": "p1",
        "kind": "wiki",
        "title": "Doc de prueba",
        "url": "https://notion.so/p1",
        "text": "hola mundo " * 50,
        "last_edited_time": "2026-06-01T00:00:00Z",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_wiki_maps_to_document() -> None:
    card = card_for_item(_item())
    assert card["type"] == "document"
    assert card["id"] == "document:p1"
    assert card["canonical_name"] == "Doc de prueba"
    assert card["source_refs"][0]["url"] == "https://notion.so/p1"
    assert card["source_refs"][0]["source_id"] == "page:p1"
    assert len(card["summary"]) <= 240


def test_ticket_maps_to_ticket() -> None:
    card = card_for_item(_item(kind="ticket", id="t9", title="Bug X"))
    assert card["type"] == "ticket"
    assert card["id"] == "ticket:t9"
    assert "ticket_detail" in card["best_tools"]


def test_meeting_maps_to_document_keeps_kind_in_source() -> None:
    card = card_for_item(_item(kind="meeting", id="m3"))
    assert card["type"] == "document"
    assert card["source_refs"][0]["source_type"] == "meeting"


def test_build_all_counts() -> None:
    cards = build_all([_item(id="a"), _item(id="b", kind="ticket")])
    assert len(cards) == 2
    for card in cards:
        assert card["id"] and card["type"] and card["canonical_name"]
