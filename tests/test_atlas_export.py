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


def test_meeting_name_is_qualified_with_date() -> None:
    """Una reunión lleva su fecha en el nombre canónico para no colapsar con
    otras instancias del mismo título recurrente."""
    card = card_for_item(
        _item(kind="meeting", id="m1", title="Reunión de producción",
              properties={"Fecha": "2026-04-27"})
    )
    assert card["canonical_name"] == "Reunión de producción (2026-04-27)"


def test_recurring_meetings_get_distinct_names() -> None:
    """Dos actas del mismo título y distinta fecha producen nombres distintos
    (no se fusionarían por alias en el atlas)."""
    a = card_for_item(_item(kind="meeting", id="a", title="Semanal T8",
                            properties={"Fecha": "2026-05-04"}))
    b = card_for_item(_item(kind="meeting", id="b", title="Semanal T8",
                            properties={"Fecha": "2026-05-11"}))
    assert a["canonical_name"] != b["canonical_name"]
    assert a["id"] != b["id"]


def test_meeting_falls_back_to_created_time_without_fecha() -> None:
    card = card_for_item(
        _item(kind="meeting", id="m2", title="Sin Fecha",
              created_time="2026-03-01T09:00:00Z")
    )
    assert card["canonical_name"] == "Sin Fecha (2026-03-01)"


def test_non_meeting_names_are_not_date_qualified() -> None:
    """Wiki y tickets conservan el título sin fecha (su título ya es único)."""
    assert card_for_item(_item())["canonical_name"] == "Doc de prueba"
    assert (
        card_for_item(_item(kind="ticket", id="t1", title="Bug X"))["canonical_name"]
        == "Bug X"
    )


def test_build_all_counts() -> None:
    cards = build_all([_item(id="a"), _item(id="b", kind="ticket")])
    assert len(cards) == 2
    for card in cards:
        assert card["id"] and card["type"] and card["canonical_name"]
