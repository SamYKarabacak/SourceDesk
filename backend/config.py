"""Application settings and local data paths."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def _env(name: str, default: str) -> str:
    for prefix in ("SOURCEDESK", "BRAVETRACE", "EVIDENCELENS"):
        value = os.getenv(f"{prefix}_{name}")
        if value is not None:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(ROOT / "data"))))
    ollama_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    )
    chat_model: str = field(default_factory=lambda: _env("CHAT_MODEL", "qwen3:4b"))
    embedding_model: str = field(default_factory=lambda: _env("EMBEDDING_MODEL", "embeddinggemma"))
    max_upload_bytes: int = 10 * 1024 * 1024
    max_text_chars: int = 1_000_000
    max_pages: int = 300
    max_documents: int = 50
    chunk_size: int = 700
    chunk_overlap: int = 120
    max_history_entries: int = 100
    ai_timeout: float = 90.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_dir", self.data_dir.expanduser().resolve())
        object.__setattr__(self, "ollama_url", self.ollama_url.rstrip("/"))
        parsed = urlparse(self.ollama_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("OLLAMA_BASE_URL must point to a local HTTP server.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            raise ValueError(
                "OLLAMA_BASE_URL must be a base address without a path or credentials."
            )
        try:
            if parsed.port == 0:
                raise ValueError("Port zero is not a model service address.")
        except ValueError as exc:
            raise ValueError("OLLAMA_BASE_URL has an invalid port.") from exc
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size.")

    @property
    def db_path(self) -> Path:
        # Keep the filename so upgrades open the existing database.
        return self.data_dir / "evidencelens.sqlite3"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"
