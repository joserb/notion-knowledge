from notion_knowledge.models import KnowledgeItem
from notion_knowledge.search import search


def _items():
    return [
        KnowledgeItem(id="1", source="wiki", kind="wiki",
                      title="Actualizacion de firmware con RAUC",
                      text="Proceso de actualizacion OTA usando RAUC y hawkBit."),
        KnowledgeItem(id="2", source="meetings", kind="meeting",
                      title="Acta sprint 26-2",
                      text="Se discutio el roadmap y los tickets pendientes."),
        KnowledgeItem(id="3", source="tickets", kind="ticket",
                      title="Bug en exportador",
                      text="El exportador CSV falla con tildes."),
    ]


def test_title_match_ranks_first():
    hits = search(_items(), "rauc firmware")
    assert hits and hits[0].item.id == "1"
    assert hits[0].score > 0


def test_filter_by_kind():
    hits = search(_items(), "tickets", kind="meeting")
    assert all(h.item.kind == "meeting" for h in hits)


def test_empty_query_returns_nothing():
    assert search(_items(), "   ") == []


def test_snippet_contains_context():
    hits = search(_items(), "OTA")
    assert hits and "OTA" in hits[0].snippet
