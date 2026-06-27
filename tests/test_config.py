from notion_knowledge.config import Config, KNOWLEDGE_KINDS


def test_load_databases_from_default_toml():
    cfg = Config.load()
    assert set(cfg.databases) == {"wiki", "meetings", "tickets"}
    assert cfg.databases["wiki"].kind == "wiki"
    assert cfg.databases["meetings"].kind == "meeting"
    assert cfg.databases["tickets"].kind == "ticket"


def test_kinds_are_known():
    cfg = Config.load()
    for db in cfg.databases.values():
        assert db.kind in KNOWLEDGE_KINDS
