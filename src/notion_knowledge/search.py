"""Busqueda full-text simple sobre la cache de conocimiento.

Sin dependencias externas: tokeniza, puntua por frecuencia de termino (con peso
extra al titulo) y devuelve resultados ordenados con un fragmento de contexto.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from notion_knowledge.models import KnowledgeItem


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize(text))


@dataclass
class SearchHit:
    item: KnowledgeItem
    score: float
    snippet: str


def _snippet(text: str, terms: set[str], width: int = 160) -> str:
    norm = _normalize(text)
    pos = -1
    for t in terms:
        pos = norm.find(t)
        if pos != -1:
            break
    if pos == -1:
        return text[:width].strip()
    start = max(0, pos - width // 2)
    end = min(len(text), pos + width // 2)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def search(
    items: list[KnowledgeItem],
    query: str,
    *,
    source: str | None = None,
    kind: str | None = None,
    limit: int = 10,
) -> list[SearchHit]:
    terms = set(_tokens(query))
    if not terms:
        return []
    hits: list[SearchHit] = []
    for item in items:
        if source and item.source != source:
            continue
        if kind and item.kind != kind:
            continue
        title_tokens = _tokens(item.title)
        body_tokens = _tokens(item.searchable_text())
        score = 0.0
        for t in terms:
            score += 3.0 * title_tokens.count(t)
            score += 1.0 * body_tokens.count(t)
        if score > 0:
            hits.append(SearchHit(item=item, score=score, snippet=_snippet(item.searchable_text(), terms)))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
