"""CLI `notion-knowledge`: notion-check, list-databases, fetch, export, search."""

from __future__ import annotations

import click

from notion_knowledge.config import Config, load_token
from notion_knowledge.markdown_export import export_items
from notion_knowledge.search import search as search_items
from notion_knowledge.store import KnowledgeStore


@click.group()
def main() -> None:
    """Recopila y consulta conocimiento interno desde Notion."""


@main.command("notion-check")
def notion_check() -> None:
    """Verifica el token y el acceso a las bases de datos configuradas."""
    from notion_knowledge.notion_client import RateLimitedNotionClient

    cfg = Config.load()
    token = load_token()
    client = RateLimitedNotionClient(token, min_interval=0)
    me = client.get_me()
    click.secho(f"Bot: {me.get('name')} ({me.get('type')})", fg="green")
    if not cfg.databases:
        click.secho("No hay bases de datos configuradas en config/default.toml.", fg="yellow")
        return
    for key, db in cfg.databases.items():
        if not db.database_id:
            click.secho(f"  [{key}/{db.kind}] omitida: sin id en config/default.toml", fg="yellow")
            continue
        try:
            info = client.get_database(db.database_id)
            title = "".join(t.get("plain_text", "") for t in info.get("title", []))
            click.secho(f"  [{key}/{db.kind}] OK: {title}", fg="green")
        except Exception as exc:  # noqa: BLE001
            click.secho(f"  [{key}] ERROR: {exc}", fg="red")


@main.command("list-databases")
def list_databases() -> None:
    """Lista las bases de datos configuradas y los items en cache."""
    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    counts = store.counts()
    if not cfg.databases:
        click.secho("Sin bases de datos configuradas (config/default.toml).", fg="yellow")
    for key, db in cfg.databases.items():
        n = counts.get(key, 0)
        click.echo(f"  {key:<12} tipo={db.kind:<8} cache={n} items  id={db.database_id or '(sin id)'}")


@main.command()
@click.option("-d", "--database", "db_key", default=None, help="Clave de base de datos; por defecto todas")
@click.option("--no-body", is_flag=True, help="No descargar el cuerpo (bloques), solo propiedades")
def fetch(db_key: str | None, no_body: bool) -> None:
    """Descarga bases de datos de Notion a la cache local."""
    from notion_knowledge.notion_client import RateLimitedNotionClient
    from notion_knowledge.fetcher import KnowledgeFetcher

    cfg = Config.load()
    token = load_token()
    fetcher = KnowledgeFetcher(RateLimitedNotionClient(token), cfg)
    if db_key:
        n = fetcher.fetch_database(db_key, with_body=not no_body)
        click.secho(f"{db_key}: {n} items descargados.", fg="green")
    else:
        for key, n in fetcher.fetch_all(with_body=not no_body).items():
            click.secho(f"{key}: {n} items.", fg="green")


@main.command()
@click.option("-d", "--database", "source", default=None, help="Exportar solo una fuente")
def export(source: str | None) -> None:
    """Exporta la cache a Markdown en data/export."""
    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    items = store.load_items(source)
    written = export_items(items, cfg.export_dir)
    click.secho(f"{len(written)} ficheros Markdown escritos en {cfg.export_dir}.", fg="green")


@main.command("tickets-stats")
@click.option("-d", "--database", "source", default="tickets", help="Fuente de tickets (clave de DB)")
@click.option("-y", "--year", type=int, default=None, help="Filtrar por anio de creacion (p. ej. 2026)")
@click.option("--tiempos", is_flag=True, help="Tambien estimar el tiempo hasta el cambio de estado")
def tickets_stats(source: str, year: int | None, tiempos: bool) -> None:
    """Segmenta los tickets por tipo, asignado, prioridad y estado."""
    from notion_knowledge import stats as st

    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    items = st.filter_by_year(store.load_items(source), year)
    if not items:
        click.secho(f"Sin tickets en cache para '{source}'"
                    f"{f' creados en {year}' if year else ''}. ¿Has hecho 'fetch'?", fg="yellow")
        return

    scope = f" (creados en {year})" if year else ""
    click.secho(f"{len(items)} tickets en '{source}'{scope}\n", fg="green", bold=True)

    def show(title: str, counter) -> None:
        click.secho(f"--- {title} ---", fg="cyan", bold=True)
        for value, n in counter.most_common():
            click.echo(f"  {n:4}  {value}")
        click.echo("")

    show("Por TIPO", st.segment(items, "Tipo"))
    show("Por ASIGNADO A", st.segment(items, "Asignado a"))
    show("Por PRIORIDAD (1-3)", st.segment_priority(items))
    show("Por ESTADO", st.segment(items, "Estado"))

    if tiempos:
        s = st.state_change_stats(items)
        click.secho("--- TIEMPO HASTA CAMBIO DE ESTADO (proxy: last_edited) ---", fg="cyan", bold=True)
        click.secho("  AVISO: Notion no guarda la fecha real de cambio de estado; "
                    "este valor es un limite superior.", fg="yellow")
        click.echo(f"  Aun en estado inicial (sin cambio): {s.still_initial}")
        click.echo(f"  Ya cambiaron de estado: {s.moved}")
        if s.days_mean is not None:
            click.echo(f"  Media: {s.days_mean:.1f} dias · Mediana: {s.days_median:.1f} dias")
        for state, (n, avg) in s.by_state.items():
            click.echo(f"    {n:4}  {avg:6.1f} dias  {state}")


@main.command("meetings-stats")
@click.option("-d", "--database", "source", default="meetings", help="Fuente de reuniones (clave de DB)")
@click.option("-y", "--year", type=int, default=None, help="Filtrar por anio de la reunion (propiedad Fecha)")
@click.option("--tendencia", is_flag=True, help="Mostrar numero de reuniones por anio")
def meetings_stats(source: str, year: int | None, tendencia: bool) -> None:
    """Segmenta las reuniones por tipo, modalidad, tema y participantes."""
    from notion_knowledge import stats as st

    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    items = st.filter_by_year(store.load_items(source), year, st.MEETING_DATE)
    if not items:
        click.secho(f"Sin reuniones en cache para '{source}'"
                    f"{f' del {year}' if year else ''}. ¿Has hecho 'fetch'?", fg="yellow")
        return

    scope = f" (del {year})" if year else ""
    click.secho(f"{len(items)} reuniones en '{source}'{scope}\n", fg="green", bold=True)

    def show(title: str, counter) -> None:
        click.secho(f"--- {title} ---", fg="cyan", bold=True)
        for value, n in counter.most_common():
            click.echo(f"  {n:5}  {value}")
        click.echo("")

    show("Por TIPO", st.segment(items, "Tipo"))
    show("Por MODALIDAD", st.segment(items, "Modalidad"))
    show("Por TEMA", st.segment(items, "Tema"))
    show("Por MODERADOR", st.segment(items, "Moderador"))
    show("Por ASISTENTES", st.segment(items, "Asistentes"))
    show("Por REDACTADO POR", st.segment(items, "Redactado por"))

    if tendencia:
        click.secho("--- REUNIONES POR ANIO (propiedad Fecha) ---", fg="cyan", bold=True)
        for y, n in sorted(st.count_by_year(items, st.MEETING_DATE).items()):
            click.echo(f"  {y}  {n}")


@main.command("notes-stats")
@click.option("-d", "--database", "source", default="notes", help="Fuente de notas (clave de DB)")
@click.option("-y", "--year", type=int, default=None, help="Filtrar por anio de la nota (propiedad Creada)")
@click.option("--tendencia", is_flag=True, help="Mostrar numero de notas por anio")
def notes_stats(source: str, year: int | None, tendencia: bool) -> None:
    """Segmenta las notas por origen, actividad, responsable y banderas."""
    from notion_knowledge import stats as st

    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    items = st.filter_by_year(store.load_items(source), year, st.NOTE_DATE)
    if not items:
        click.secho(f"Sin notas en cache para '{source}'"
                    f"{f' del {year}' if year else ''}. ¿Has hecho 'fetch'?", fg="yellow")
        return

    scope = f" (del {year})" if year else ""
    click.secho(f"{len(items)} notas en '{source}'{scope}\n", fg="green", bold=True)

    def show(title: str, counter) -> None:
        click.secho(f"--- {title} ---", fg="cyan", bold=True)
        for value, n in counter.most_common():
            click.echo(f"  {n:5}  {value}")
        click.echo("")

    show("Por ORIGEN", st.segment(items, "Origen"))
    show("Por ACTIVIDAD", st.segment(items, "Actividad"))
    show("Por RESPONSABLE", st.segment(items, "Responsable"))
    show("IMPORTANTE", st.segment(items, "Importante"))
    show("ARCHIVADA", st.segment(items, "Archivada"))

    if tendencia:
        click.secho("--- NOTAS POR ANIO (propiedad Creada) ---", fg="cyan", bold=True)
        for y, n in sorted(st.count_by_year(items, st.NOTE_DATE).items()):
            click.echo(f"  {y}  {n}")


@main.command()
@click.argument("query")
@click.option("-d", "--database", "source", default=None, help="Filtrar por fuente")
@click.option("-k", "--kind", default=None, help="Filtrar por tipo (wiki|meeting|ticket)")
@click.option("-n", "--limit", default=10, help="Numero de resultados")
def search(query: str, source: str | None, kind: str | None, limit: int) -> None:
    """Busca en la cache de conocimiento."""
    cfg = Config.load()
    store = KnowledgeStore(cfg.cache_dir)
    hits = search_items(store.load_items(), query, source=source, kind=kind, limit=limit)
    if not hits:
        click.secho("Sin resultados (¿has hecho 'fetch'?).", fg="yellow")
        return
    for h in hits:
        click.secho(f"[{h.score:.0f}] {h.item.title}", fg="cyan", bold=True)
        click.echo(f"      {h.item.kind} · {h.item.source} · {h.item.url}")
        click.echo(f"      {h.snippet}")


if __name__ == "__main__":
    main()
