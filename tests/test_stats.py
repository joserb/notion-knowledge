from notion_knowledge.models import KnowledgeItem
from notion_knowledge import stats as st


def _ticket(tid, *, tipo=None, asignado=None, prioridad=None, estado=None,
            created="2026-01-01T00:00:00.000Z", edited="2026-01-11T00:00:00.000Z"):
    props = {"Tipo": tipo, "Asignado a": asignado, "Prioridad": prioridad, "Estado": estado}
    return KnowledgeItem(id=tid, source="tickets", kind="ticket", title=f"t-{tid}",
                         created_time=created, last_edited_time=edited, properties=props)


def test_segment_counts_single_and_multivalue():
    items = [
        _ticket("1", tipo="Calidad", asignado=["Ana", "Luis"]),
        _ticket("2", tipo="Calidad", asignado=["Ana"]),
        _ticket("3", tipo=None, asignado=[]),
    ]
    assert st.segment(items, "Tipo") == {"Calidad": 2, "(vacío)": 1}
    asignado = st.segment(items, "Asignado a")
    assert asignado["Ana"] == 2 and asignado["Luis"] == 1 and asignado["(vacío)"] == 1


def test_priority_levels_from_stars():
    items = [_ticket("1", prioridad="⭐️"), _ticket("2", prioridad="⭐️⭐️⭐️"), _ticket("3")]
    assert st.priority_level(items[0]) == 1
    assert st.priority_level(items[1]) == 3
    assert st.priority_level(items[2]) is None
    assert st.segment_priority(items) == {"1": 1, "3": 1, "(sin prioridad)": 1}


def test_filter_by_year():
    items = [_ticket("1", created="2026-03-01T00:00:00Z"),
             _ticket("2", created="2025-09-01T00:00:00Z")]
    assert [i.id for i in st.filter_by_year(items, 2026)] == ["1"]
    assert len(st.filter_by_year(items, None)) == 2


def _meeting(mid, *, fecha=None, tipo=None, asistentes=None):
    props = {"Fecha": fecha, "Tipo": tipo, "Asistentes": asistentes}
    return KnowledgeItem(id=mid, source="meetings", kind="meeting", title=f"m-{mid}",
                         created_time="2099-01-01T00:00:00Z", properties=props)


def test_filter_by_year_uses_meeting_date():
    # created_time es 2099 a proposito: el filtro debe usar la propiedad Fecha.
    items = [_meeting("1", fecha="2026-02-01"), _meeting("2", fecha="2024-05-01")]
    got = st.filter_by_year(items, 2026, st.MEETING_DATE)
    assert [i.id for i in got] == ["1"]


def test_count_by_year_meetings():
    items = [_meeting("1", fecha="2026-01-01"), _meeting("2", fecha="2026-09-01"),
             _meeting("3", fecha="2024-01-01"), _meeting("4", fecha=None)]
    counts = st.count_by_year(items, st.MEETING_DATE)
    assert counts["2026"] == 2 and counts["2024"] == 1 and counts["(sin fecha)"] == 1


def test_ticket_summary_with_timing():
    items = [
        _ticket("1", tipo="Calidad", prioridad="⭐️⭐️", estado="Nuevo"),
        _ticket("2", tipo="Técnico", prioridad="⭐️", estado="Completado",
                created="2026-01-01T00:00:00Z", edited="2026-01-11T00:00:00Z"),
    ]
    s = st.ticket_summary(items, with_timing=True)
    assert s["total"] == 2
    assert s["by_type"] == {"Calidad": 1, "Técnico": 1}
    assert s["by_priority"]["2"] == 1
    assert s["state_change"]["moved"] == 1
    assert s["state_change"]["days_mean"] == 10.0


def test_meeting_summary_with_trend():
    items = [_meeting("1", fecha="2026-01-01", tipo="Seguimiento", asistentes=["Ana"]),
             _meeting("2", fecha="2026-02-01", tipo="Diseño", asistentes=["Ana", "Luis"])]
    s = st.meeting_summary(items, with_trend=True)
    assert s["total"] == 2
    assert s["by_attendee"]["Ana"] == 2 and s["by_attendee"]["Luis"] == 1
    assert s["by_year"] == {"2026": 2}


def _note(nid, *, creada=None, origen=None, actividad=None, responsable=None, importante=None):
    props = {"Creada": creada, "Origen": origen, "Actividad": actividad,
             "Responsable": responsable, "Importante": importante, "Archivada": False}
    return KnowledgeItem(id=nid, source="notes", kind="note", title=f"n-{nid}",
                         created_time="2099-01-01T00:00:00Z", properties=props)


def test_filter_by_year_uses_note_date():
    items = [_note("1", creada="2026-04-01T00:00:00Z"), _note("2", creada="2022-04-01T00:00:00Z")]
    assert [i.id for i in st.filter_by_year(items, 2026, st.NOTE_DATE)] == ["1"]


def test_note_summary_with_trend():
    items = [_note("1", creada="2026-01-01T00:00:00Z", origen="Interno",
                   actividad=["Desarrollo"], responsable=["Ana"], importante=True),
             _note("2", creada="2025-01-01T00:00:00Z", origen="Cliente",
                   actividad=["Comercial"], responsable=["Ana", "Luis"], importante=False)]
    s = st.note_summary(items, with_trend=True)
    assert s["total"] == 2
    assert s["by_origin"] == {"Interno": 1, "Cliente": 1}
    assert s["by_owner"]["Ana"] == 2
    assert s["important"] == {"True": 1, "False": 1}
    assert s["by_year"] == {"2025": 1, "2026": 1}


def test_state_change_stats_excludes_initial_state():
    items = [
        _ticket("1", estado="Nuevo"),                                  # sin cambio
        _ticket("2", estado="Completado",                              # 10 dias
                created="2026-01-01T00:00:00Z", edited="2026-01-11T00:00:00Z"),
        _ticket("3", estado="Descartado",                              # 20 dias
                created="2026-01-01T00:00:00Z", edited="2026-01-21T00:00:00Z"),
    ]
    s = st.state_change_stats(items)
    assert s.still_initial == 1
    assert s.moved == 2
    assert s.days_mean == 15.0
    assert s.by_state["Completado"] == (1, 10.0)
