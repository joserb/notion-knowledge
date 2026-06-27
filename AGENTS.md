# AGENTS.md — notion-knowledge

Convenciones para trabajar (humanos y agentes) en este repo.

## Qué es

PoC de dominio que recopila conocimiento interno desde Notion (wiki, actas, tickets
entre equipos) y lo expone a `twave-agent-hub`. Hermano de `notion-cycles-review`,
del que reutiliza el cliente Notion y el patrón de configuración.

## Convenciones técnicas

- Python ≥ 3.10 (objetivo 3.12), `uv`, layout `src/`, CLI con `click`, tests `pytest`.
- Prosa y documentación en español; identificadores y claves en inglés.
- Secretos solo por variable de entorno (`NOTION_TOKEN`); nunca en el código.

## Contrato con el hub

- `tool_manifest.yml` (raíz) declara capacidades, entidades y nivel de acceso.
- `src/notion_knowledge/agent_adapter.py` lee un ToolRequest por STDIN y devuelve un
  ToolResponse por STDOUT, respondiendo desde la caché local.
- Toda respuesta incluye fuentes, entidades, advertencias, confianza y acciones.

## Reglas

- Read-only por defecto: este repo no escribe en Notion.
- Mantén el manifiesto sincronizado con las capacidades reales del adaptador.
- `fetch` actualiza la caché (`data/raw`), que está en `.gitignore` (no se versiona).

## Estructura

Cliente/parsing en `notion_client.py`/`notion_text.py`; dominio en `models.py`;
descarga en `fetcher.py`; caché en `store.py`; búsqueda en `search.py`; export en
`markdown_export.py`; CLI en `cli.py`.
