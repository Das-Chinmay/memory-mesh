import json
from pathlib import Path
from memory_mesh.config import Config


def test_default_config():
    cfg = Config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8765
    assert cfg.similarity_threshold == 0.85
    assert cfg.diff_ratio_threshold == 0.20
    assert cfg.nli_enabled is False
    assert cfg.auth_enabled is False
    assert cfg.auth_token is None


def test_db_path_is_under_data_dir():
    cfg = Config()
    assert cfg.db_path == cfg.data_dir / "memories.db"
    assert cfg.chroma_path == cfg.data_dir / "chroma"


def test_load_from_file(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"port": 9000, "nli_enabled": True}))
    cfg = Config.load(config_path=config_file)
    assert cfg.port == 9000
    assert cfg.nli_enabled is True
    assert cfg.host == "127.0.0.1"  # default preserved


def test_save_and_reload(tmp_path):
    cfg = Config(port=9001, data_dir=tmp_path)
    cfg.save()
    cfg2 = Config.load(config_path=tmp_path / "config.json")
    assert cfg2.port == 9001


def test_missing_config_file_returns_defaults(tmp_path):
    cfg = Config.load(config_path=tmp_path / "nonexistent.json")
    assert cfg.port == 8765
