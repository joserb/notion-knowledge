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
