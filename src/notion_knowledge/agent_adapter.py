"""Adaptador de contrato para twave-agent-hub.

Lee un ToolRequest (JSON) por STDIN y escribe un ToolResponse (JSON) por STDOUT.
Responde desde la cache local (data/raw), sin requerir acceso en vivo a Notion.
Capacidades: search_knowledge, get_document, list_sources, stats.
"""

from __future__ import annotations

import json
import sys
import time

from notion_knowledge import stats as st
from notion_knowledge.config import Config
from notion_knowledge.search import search as search_items
from notion_knowledge.store import KnowledgeStore


def _envelope(req, status, result, **extra):
    resp = {
        "request_id": req.get("request_id", ""),
        "tool": "notion-knowledge",
        "capability": req.get("capability", ""),
        "status": status,
        "result": result,
        "sources": [],
        "entities": [],
        "warnings": [],
        "confidence": 0.9 if status == "ok" else 0.0,
        "suggested_actions": [],
        "meta": {"tool_version": "0.1.0"},
    }
    resp.update(extra)
    return resp


def _error(req, message, code="adapter_error"):
    return _envelope(
        req, "error", {"error": {"code": code, "message": message}},
        warnings=[{"code": code, "severity": "critical", "message": message}],
        confidence=0.0,
    )


def _kind_to_entity(kind: str) -> str:
    return {"ticket": "ticket"}.get(kind, "document")


def _store() -> KnowledgeStore:
    cfg = Config.load()
    return KnowledgeStore(cfg.cache_dir)


def cap_list_sources(req):
    store = _store()
    counts = store.counts()
    return _envelope(
        req, "ok", {"sources": counts, "total": sum(counts.values())},
        sources=[{
            "id": "notion_knowledge_cache", "kind": "file_folder",
            "title": "Cache local de conocimiento",
            "reference": "notion-cache://data/raw",
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }],
    )


def cap_search_knowledge(req):
    payload = req.get("payload") or {}
    query = payload.get("query")
    if not query:
        return _error(req, "Falta el parametro 'query'.", "missing_param")
    store = _store()
    hits = search_items(
        store.load_items(), query,
        source=payload.get("source"), kind=payload.get("kind"),
        limit=int(payload.get("limit", 10)),
    )
    result = {
        "query": query,
        "count": len(hits),
        "hits": [
            {"id": h.item.id, "title": h.item.title, "kind": h.item.kind,
             "source": h.item.source, "url": h.item.url, "snippet": h.snippet,
             "score": h.score}
            for h in hits
        ],
    }
    sources = [{
        "id": f"page:{h.item.id}", "kind": "notion_page",
        "title": h.item.title, "reference": h.item.url or f"notion://page/{h.item.id}",
        "retrieved_at": h.item.last_edited_time or "",
    } for h in hits]
    entities = [{
        "type": _kind_to_entity(h.item.kind), "id": h.item.id,
        "label": h.item.title, "confidence": 0.8,
    } for h in hits]
    warnings = []
    if not hits:
        warnings.append({"code": "no_results", "severity": "info",
                         "message": "Sin resultados; ¿se ha ejecutado 'fetch'?"})
    return _envelope(req, "ok", result, sources=sources, entities=entities,
                     warnings=warnings, confidence=0.85 if hits else 0.3)


def cap_get_document(req):
    payload = req.get("payload") or {}
    item_id = payload.get("id")
    if not item_id:
        return _error(req, "Falta el parametro 'id'.", "missing_param")
    item = _store().get_item(item_id)
    if item is None:
        return _error(req, f"Documento no encontrado en cache: {item_id}", "not_found")
    return _envelope(
        req, "ok", item.to_dict(),
        sources=[{
            "id": f"page:{item.id}", "kind": "notion_page", "title": item.title,
            "reference": item.url or f"notion://page/{item.id}",
            "retrieved_at": item.last_edited_time or "",
        }],
        entities=[{"type": _kind_to_entity(item.kind), "id": item.id,
                   "label": item.title, "confidence": 0.95}],
    )


def cap_stats(req):
    """Segmenta tickets o reuniones desde la cache (conteos por propiedad)."""
    payload = req.get("payload") or {}
    source = payload.get("source")
    if source not in ("tickets", "meetings", "notes"):
        return _error(req, "Parametro 'source' debe ser 'tickets', 'meetings' o 'notes'.", "missing_param")
    year = payload.get("year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        return _error(req, "El parametro 'year' debe ser un entero.", "bad_request")

    store = _store()
    if source == "tickets":
        items = st.filter_by_year(store.load_items(source), year, st.TICKET_DATE)
        result = st.ticket_summary(items, with_timing=bool(payload.get("timing")))
    elif source == "meetings":
        items = st.filter_by_year(store.load_items(source), year, st.MEETING_DATE)
        result = st.meeting_summary(items, with_trend=bool(payload.get("trend")))
    else:
        items = st.filter_by_year(store.load_items(source), year, st.NOTE_DATE)
        result = st.note_summary(items, with_trend=bool(payload.get("trend")))
    result["source"] = source
    result["year"] = year

    warnings = []
    if not items:
        warnings.append({"code": "no_results", "severity": "info",
                         "message": "Sin items en cache; ¿se ha ejecutado 'fetch'?"})
    return _envelope(req, "ok", result, warnings=warnings,
                     confidence=0.9 if items else 0.3)


CAPABILITIES = {
    "search_knowledge": cap_search_knowledge,
    "get_document": cap_get_document,
    "list_sources": cap_list_sources,
    "stats": cap_stats,
}


def handle(req):
    fn = CAPABILITIES.get(req.get("capability"))
    if fn is None:
        return _error(req, f"Capacidad desconocida: {req.get('capability')}", "unknown_capability")
    return fn(req)


def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        print(json.dumps(_error({}, f"STDIN no es JSON valido: {exc}", "bad_request")))
        return
    print(json.dumps(handle(req), ensure_ascii=False))


if __name__ == "__main__":
    main()
