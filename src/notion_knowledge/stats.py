"""Estadisticas de tickets: segmentacion por tipo, asignado, prioridad y estado.

Trabaja sobre la cache local (`KnowledgeItem`), sin tocar Notion. Pensado para la
base de datos de tickets, pero las funciones son genericas sobre propiedades.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median
from typing import Callable

from notion_knowledge.models import KnowledgeItem

# La prioridad se guarda en Notion como estrellas; la normalizamos a 1..3.
PRIORITY_STARS = {"⭐️": 1, "⭐️⭐️": 2, "⭐️⭐️⭐️": 3}

# Estado inicial del que parten los tickets; el resto cuenta como "ya cambiado".
INITIAL_STATE = "Nuevo"

# Accesores de fecha: los tickets usan la fecha de creacion de la pagina; las
# reuniones usan su propiedad "Fecha" (la fecha real de la reunion, no la de alta).
DateOf = Callable[[KnowledgeItem], "str | None"]
TICKET_DATE: DateOf = lambda i: i.created_time
MEETING_DATE: DateOf = lambda i: i.properties.get("Fecha")
NOTE_DATE: DateOf = lambda i: i.properties.get("Creada")


def priority_level(item: KnowledgeItem) -> int | None:
    """Devuelve la prioridad como 1..3, o None si no esta definida."""
    return PRIORITY_STARS.get(item.properties.get("Prioridad"))


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def segment(items: list[KnowledgeItem], prop: str) -> Counter:
    """Cuenta items por valor de una propiedad.

    Soporta propiedades de un solo valor y multivalor (listas, p. ej. "Asignado a").
    Los valores vacios se agrupan bajo "(vacío)".
    """
    counter: Counter = Counter()
    for item in items:
        value = item.properties.get(prop)
        if isinstance(value, list):
            for entry in (value or ["(vacío)"]):
                counter[str(entry)] += 1
        else:
            # Normalizamos a texto: evita claves booleanas (que en JSON saldrian
            # como "true"/"false") y mantiene la salida consistente.
            counter["(vacío)" if value in (None, "") else str(value)] += 1
    return counter


def segment_priority(items: list[KnowledgeItem]) -> Counter:
    """Cuenta items por prioridad normalizada (1..3) o "(sin prioridad)"."""
    counter: Counter = Counter()
    for item in items:
        level = priority_level(item)
        counter[f"{level}" if level else "(sin prioridad)"] += 1
    return counter


def filter_by_year(
    items: list[KnowledgeItem], year: int | None, date_of: DateOf = TICKET_DATE
) -> list[KnowledgeItem]:
    """Filtra por anio de una fecha. Si year es None, no filtra.

    `date_of` elige el campo de fecha: por defecto `created_time` (tickets); para
    reuniones pasar `MEETING_DATE` (propiedad "Fecha").
    """
    if year is None:
        return items
    prefix = str(year)
    return [i for i in items if (date_of(i) or "").startswith(prefix)]


def count_by_year(items: list[KnowledgeItem], date_of: DateOf = TICKET_DATE) -> Counter:
    """Cuenta items por anio de una fecha (tendencia temporal)."""
    counter: Counter = Counter()
    for item in items:
        value = date_of(item) or ""
        counter[value[:4] if value else "(sin fecha)"] += 1
    return counter


@dataclass
class StateChangeStats:
    """Tiempo desde la creacion hasta el cambio de estado (proxy: last_edited).

    AVISO: Notion no expone la fecha real de cambio de estado de una propiedad, asi
    que se usa `last_edited_time` como aproximacion. Captura *cualquier* edicion
    posterior, por lo que el resultado es un LIMITE SUPERIOR del tiempo real.
    """

    total: int = 0
    still_initial: int = 0
    moved: int = 0
    days_mean: float | None = None
    days_median: float | None = None
    by_state: dict[str, tuple[int, float]] = field(default_factory=dict)


def state_change_stats(items: list[KnowledgeItem]) -> StateChangeStats:
    """Calcula el tiempo medio/mediano hasta el cambio de estado (proxy)."""
    stats = StateChangeStats(total=len(items))
    deltas: list[float] = []
    by_state: dict[str, list[float]] = defaultdict(list)
    for item in items:
        state = item.properties.get("Estado")
        if state in (None, INITIAL_STATE):
            stats.still_initial += 1
            continue
        created = _parse_dt(item.created_time)
        edited = _parse_dt(item.last_edited_time)
        if not (created and edited and edited >= created):
            continue
        days = (edited - created).total_seconds() / 86400
        deltas.append(days)
        by_state[state].append(days)
    stats.moved = len(deltas)
    if deltas:
        stats.days_mean = mean(deltas)
        stats.days_median = median(deltas)
    stats.by_state = {
        s: (len(ds), mean(ds)) for s, ds in sorted(by_state.items(), key=lambda x: -len(x[1]))
    }
    return stats


def _ordered(counter: Counter) -> dict:
    """Counter -> dict ordenado por frecuencia descendente (serializable a JSON)."""
    return dict(counter.most_common())


def ticket_summary(items: list[KnowledgeItem], *, with_timing: bool = False) -> dict:
    """Resumen de tickets segmentado, listo para serializar a JSON."""
    summary: dict = {
        "total": len(items),
        "by_type": _ordered(segment(items, "Tipo")),
        "by_assignee": _ordered(segment(items, "Asignado a")),
        "by_priority": _ordered(segment_priority(items)),
        "by_state": _ordered(segment(items, "Estado")),
    }
    if with_timing:
        s = state_change_stats(items)
        summary["state_change"] = {
            "proxy": "last_edited_time",
            "note": ("Notion no guarda la fecha real de cambio de estado; "
                     "este tiempo es un limite superior."),
            "still_initial": s.still_initial,
            "moved": s.moved,
            "days_mean": s.days_mean,
            "days_median": s.days_median,
            "by_state": {st: {"count": n, "days_mean": avg} for st, (n, avg) in s.by_state.items()},
        }
    return summary


def meeting_summary(items: list[KnowledgeItem], *, with_trend: bool = False) -> dict:
    """Resumen de reuniones segmentado, listo para serializar a JSON."""
    summary: dict = {
        "total": len(items),
        "by_type": _ordered(segment(items, "Tipo")),
        "by_modality": _ordered(segment(items, "Modalidad")),
        "by_topic": _ordered(segment(items, "Tema")),
        "by_moderator": _ordered(segment(items, "Moderador")),
        "by_attendee": _ordered(segment(items, "Asistentes")),
        "by_author": _ordered(segment(items, "Redactado por")),
    }
    if with_trend:
        summary["by_year"] = dict(sorted(count_by_year(items, MEETING_DATE).items()))
    return summary


def note_summary(items: list[KnowledgeItem], *, with_trend: bool = False) -> dict:
    """Resumen de notas segmentado, listo para serializar a JSON."""
    summary: dict = {
        "total": len(items),
        "by_origin": _ordered(segment(items, "Origen")),
        "by_activity": _ordered(segment(items, "Actividad")),
        "by_owner": _ordered(segment(items, "Responsable")),
        "important": _ordered(segment(items, "Importante")),
        "archived": _ordered(segment(items, "Archivada")),
    }
    if with_trend:
        summary["by_year"] = dict(sorted(count_by_year(items, NOTE_DATE).items()))
    return summary
