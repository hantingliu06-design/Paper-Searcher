"""Environment-only credentials. Nothing secret crosses the browser boundary."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_env(path: Path = Path(".env")) -> None:
    """Load a minimal dotenv file without executing shell code or replacing env vars."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key.replace("_", "").isalnum() and key[0].isalpha():
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(default="", repr=False)
    openai_model: str = ""
    openalex_api_key: str = field(default="", repr=False)
    serpapi_key: str = field(default="", repr=False)
    impact_factor_file: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "").strip(),
            openalex_api_key=os.getenv("OPENALEX_API_KEY", "").strip(),
            serpapi_key=os.getenv("SERPAPI_API_KEY", "").strip(),
            impact_factor_file=os.getenv("IMPACT_FACTOR_FILE", "").strip(),
        )

    def public(self) -> dict:
        return {
            "openai": bool(self.openai_api_key and self.openai_model),
            "openalex": bool(self.openalex_api_key),
            "scholar": bool(self.serpapi_key),
            "impact_factors": bool(self.impact_factor_file),
        }
