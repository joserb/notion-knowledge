# Export al twave-knowledge-atlas

Este gateway exporta **entity cards** de conocimiento (documentos/actas → `document`,
y `ticket`) para el `twave-knowledge-atlas`, desde la caché local (`data/raw`), sin
acceso en vivo a Notion.

## Generar el export

```bash
uv run python -m notion_knowledge.atlas_export                 # todo
uv run python -m notion_knowledge.atlas_export --source tickets
uv run python -m notion_knowledge.atlas_export --out ruta.jsonl
```

Salida por defecto: `data/exports/entity_cards.jsonl`. Solo escribe el JSONL local.

Las actas de reunión se modelan como `document` (el hub no contempla `meeting`); el
matiz se conserva en `source_refs[].source_type`.

## Ingerir en el atlas

```bash
atlas import <ruta>/data/exports/entity_cards.jsonl
atlas merge && atlas build-vault
```

Formato y convención común: ver `twave-knowledge-atlas/docs/gateway_exports.md`.
Cards conformes a `twave-knowledge-atlas/schemas/entity_card.schema.json`.
También expuesto como capacidad `export_entity_cards` en `tool_manifest.yml`.
