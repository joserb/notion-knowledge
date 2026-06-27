# notion-knowledge

Recopila y consulta **conocimiento interno de TWave** desde Notion: wiki/
documentación, actas de reunión y tickets entre equipos. Mantiene una caché local,
exporta a Markdown (estilo Obsidian) y ofrece búsqueda/Q&A. Se integra con
`twave-agent-hub` mediante un adaptador de contrato.

Comparte andamiaje con `notion-cycles-review` (cliente Notion rate-limited, patrón de
configuración y `names.toml`), pero apunta a **otras bases de datos** y a otro uso:
aquí el objetivo es buscar y reutilizar conocimiento, no auditar ciclos.

## Requisitos

- Python ≥ 3.10 (recomendado 3.12), [uv](https://docs.astral.sh/uv/)
- Un token de integración de Notion con acceso a las bases de datos configuradas

## Configuración

1. Copia `config/.env.example` a `config/.env` y pon tu `NOTION_TOKEN`.
2. En `config/default.toml`, rellena el `id` de cada base de datos (wiki, meetings,
   tickets) y su `type`.

## Uso

```bash
uv sync

uv run notion-knowledge notion-check          # verifica token y acceso a las DBs
uv run notion-knowledge list-databases         # DBs configuradas + items en caché
uv run notion-knowledge fetch                   # descarga todas las DBs a la caché
uv run notion-knowledge fetch -d wiki           # solo una DB
uv run notion-knowledge export                  # caché -> Markdown en data/export
uv run notion-knowledge search "actualizacion firmware"   # búsqueda full-text
uv run notion-knowledge search "rauc" -k wiki -n 5

uv run notion-knowledge tickets-stats                   # segmenta tickets (tipo/asignado/prioridad/estado)
uv run notion-knowledge tickets-stats -y 2026 --tiempos  # solo 2026 + proxy de tiempo de cambio de estado
uv run notion-knowledge meetings-stats                  # segmenta reuniones (tipo/modalidad/tema/participantes)
uv run notion-knowledge meetings-stats -y 2026 --tendencia  # solo 2026 + nº de reuniones por año
uv run notion-knowledge notes-stats                     # segmenta notas (origen/actividad/responsable/banderas)
uv run notion-knowledge notes-stats -y 2026 --tendencia  # solo 2026 + nº de notas por año
```

> `tickets-stats` mapea la prioridad de estrellas a 1–3. El proxy `--tiempos` usa
> `last_edited_time` (Notion no guarda la fecha real de cambio de estado), así que es
> un **límite superior**. `meetings-stats` filtra por la propiedad `Fecha` de la reunión.

## Integración con twave-agent-hub

El manifiesto (`tool_manifest.yml`) y el adaptador (`agent_adapter.py`) exponen la
herramienta al hub con cuatro capacidades read-only: `search_knowledge`, `get_document`,
`list_sources` y `stats`. El adaptador responde desde la caché local (sin Notion en vivo).

```bash
echo '{"request_id":"r1","tool":"notion-knowledge","capability":"search_knowledge",
       "payload":{"query":"rauc"}}' | uv run python -m notion_knowledge.agent_adapter

# Segmentaciones (tickets o reuniones) como JSON para el agente:
echo '{"capability":"stats","payload":{"source":"tickets","year":2026,"timing":true}}' \
  | uv run python -m notion_knowledge.agent_adapter
echo '{"capability":"stats","payload":{"source":"meetings","trend":true}}' \
  | uv run python -m notion_knowledge.agent_adapter
```

## Estructura

```
notion-knowledge/
├── config/            .env.example, default.toml (DBs), names.toml
├── src/notion_knowledge/
│   ├── notion_client.py     Cliente Notion rate-limited (reutilizado)
│   ├── config.py            Carga de token y de bases de datos
│   ├── models.py            KnowledgeItem
│   ├── notion_text.py       Extracción de texto de propiedades y bloques
│   ├── fetcher.py           Descarga DB -> caché
│   ├── store.py             Caché local (data/raw)
│   ├── search.py            Búsqueda full-text
│   ├── markdown_export.py   Export a Markdown
│   ├── agent_adapter.py     Adaptador de contrato para el hub
│   └── cli.py               CLI notion-knowledge
├── tests/
└── tool_manifest.yml  Manifiesto para twave-agent-hub
```
