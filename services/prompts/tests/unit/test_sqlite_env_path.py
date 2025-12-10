import os
from prompt_manager.utils.config import load_config
from prompt_manager.dal.database import Database


def test_sqlite_path_env_placeholder(tmp_path):
    db_file = tmp_path / "env_prompts.db"
    os.environ["PROMPT_MANAGER_DB_PATH"] = str(db_file)

    content = """
    [database]
    type = "sqlite"
    path = "${PROMPT_MANAGER_DB_PATH}"
    pool_size = 2
    max_overflow = 1

    [vector]
    enabled = true
    dimension = 16
    embedding_model = "text-embedding-3-small"

    [cache]
    enabled = false

    [concurrency]
    queue_enabled = false

    [logging]
    level = "INFO"

    [api.http]
    enabled = false
    """

    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(content, encoding="utf-8")

    cfg = load_config(str(cfg_path))
    assert cfg.database.path == str(db_file)

    db = Database(cfg.database)
    assert db.url.endswith(str(db_file))
    assert db.engine is not None
    assert os.path.exists(db_file)
