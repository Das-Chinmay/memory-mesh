from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path.home() / ".memory-mesh")
    similarity_threshold: float = 0.85
    diff_ratio_threshold: float = 0.20
    nli_enabled: bool = False
    nli_model: str = "cross-encoder/nli-deberta-v3-small"
    host: str = "127.0.0.1"
    port: int = 8765
    auth_enabled: bool = False
    auth_token: str | None = None

    @property
    def db_path(self) -> Path:
        return self.data_dir / "memories.db"

    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        if config_path is None:
            config_path = Path.home() / ".memory-mesh" / "config.json"
        if not config_path.exists():
            return cls()
        data = json.loads(config_path.read_text())
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if "data_dir" in filtered:
            filtered["data_dir"] = Path(filtered["data_dir"])
        return cls(**filtered)

    def save(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = self.data_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        raw = asdict(self)
        raw["data_dir"] = str(raw["data_dir"])
        config_path.write_text(json.dumps(raw, indent=2))
