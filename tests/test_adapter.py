import json
from pathlib import Path

import notion_knowledge.agent_adapter as adapter
from notion_knowledge.config import Config
from notion_knowledge.models import KnowledgeItem
from notion_knowledge.store import KnowledgeStore


def _seed(tmp_path: Path, monkeypatch):
    store = KnowledgeStore(tmp_path)
    store.save_item(KnowledgeItem(id="t1", source="tickets", kind="ticket", title="Bug",
                                  created_time="2026-01-01T00:00:00Z",
                                  last_edited_time="2026-01-06T00:00:00Z",
                                  properties={"Tipo": "Calidad", "Prioridad": "⭐️⭐️",
                                              "Estado": "Completado", "Asignado a": ["Ana"]}))
    store.save_item(KnowledgeItem(id="m1", source="meetings", kind="meeting", title="Daily",
                                  properties={"Fecha": "2026-03-01", "Tipo": "Seguimiento",
                                              "Modalidad": "Online", "Asistentes": ["Ana"]}))
    store.save_item(KnowledgeItem(id="n1", source="notes", kind="note", title="Idea",
                                  properties={"Creada": "2026-05-01T00:00:00Z", "Origen": "Interno",
                                              "Actividad": ["Desarrollo"], "Responsable": ["Ana"],
                                              "Importante": True, "Archivada": False}))
    monkeypatch.setattr(adapter, "_store", lambda: store)


def test_stats_tickets(tmp_path: Path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    req = {"request_id": "r1", "capability": "stats",
           "payload": {"source": "tickets", "year": 2026, "timing": True}}
    resp = adapter.handle(req)
    assert resp["status"] == "ok"
    assert resp["result"]["total"] == 1
    assert resp["result"]["by_priority"]["2"] == 1
    assert resp["result"]["state_change"]["moved"] == 1
    # serializable a JSON
    json.dumps(resp, ensure_ascii=False)


def test_stats_meetings(tmp_path: Path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    resp = adapter.handle({"capability": "stats",
                           "payload": {"source": "meetings", "trend": True}})
    assert resp["status"] == "ok"
    assert resp["result"]["by_modality"]["Online"] == 1
    assert resp["result"]["by_year"] == {"2026": 1}


def test_stats_notes(tmp_path: Path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    resp = adapter.handle({"capability": "stats",
                           "payload": {"source": "notes", "year": 2026, "trend": True}})
    assert resp["status"] == "ok"
    assert resp["result"]["by_origin"]["Interno"] == 1
    assert resp["result"]["important"]["True"] == 1
    assert resp["result"]["by_year"] == {"2026": 1}


def test_stats_rejects_bad_source(tmp_path: Path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    resp = adapter.handle({"capability": "stats", "payload": {"source": "wiki"}})
    assert resp["status"] == "error"
    assert resp["result"]["error"]["code"] == "missing_param"


def test_unknown_capability():
    resp = adapter.handle({"capability": "nope"})
    assert resp["status"] == "error"
    assert resp["result"]["error"]["code"] == "unknown_capability"
