"""
Config loader.

Priority:
    ENV > local.yaml > default.yaml

Usage:
    from config import cfg

    cfg.api_key
    cfg.generator_model
"""

from __future__ import annotations

import os
from pathlib import Path
import yaml
from dotenv import load_dotenv


# Load .env
load_dotenv(override=True)


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base.
    """
    result = base.copy()

    for k, v in override.items():
        if (
            isinstance(v, dict)
            and isinstance(result.get(k), dict)
        ):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v

    return result


def _load() -> dict:
    config_dir = Path(__file__).parent

    default_path = config_dir / "default.yaml"
    local_path = config_dir / "local.yaml"

    data = {}

    if default_path.exists():
        data = yaml.safe_load(
            default_path.read_text(encoding="utf-8")
        ) or {}

    if local_path.exists():
        local_data = yaml.safe_load(
            local_path.read_text(encoding="utf-8")
        ) or {}

        data = _deep_merge(data, local_data)

    return data


class Config:
    def __init__(self, data: dict):
        self._data = data

    # -------------------------------------------------
    # OpenRouter
    # -------------------------------------------------

    @property
    def api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def base_url(self) -> str:
        return self._data.get(
            "openrouter",
            {}
        ).get(
            "base_url",
            "https://openrouter.ai/api/v1"
        )

    @property
    def referer(self) -> str:
        return self._data.get(
            "openrouter",
            {}
        ).get(
            "referer",
            ""
        )

    @property
    def title(self) -> str:
        return self._data.get(
            "openrouter",
            {}
        ).get(
            "title",
            "DRS v3"
        )

    # -------------------------------------------------
    # Models
    # -------------------------------------------------

    @property
    def generator_model(self) -> str:
        return self._data.get(
            "models",
            {}
        ).get(
            "generator",
            "google/gemini-2.5-flash"
        )

    @property
    def reviewer_model(self) -> str:
        return self._data.get(
            "models",
            {}
        ).get(
            "reviewer",
            "google/gemini-2.5-flash"
        )

    @property
    def ocr_model(self) -> str:
        return self._data.get(
            "models",
            {}
        ).get(
            "ocr",
            "google/gemini-2.5-flash:free"
        )

    # -------------------------------------------------
    # Generation
    # -------------------------------------------------

    @property
    def gen_max_tokens(self) -> int:
        return self._data.get(
            "generation",
            {}
        ).get(
            "max_tokens",
            2048
        )

    @property
    def gen_temperature(self) -> float:
        return self._data.get(
            "generation",
            {}
        ).get(
            "temperature",
            0.3
        )

    # -------------------------------------------------
    # Review
    # -------------------------------------------------

    @property
    def review_max_tokens(self) -> int:
        return self._data.get(
            "review",
            {}
        ).get(
            "max_tokens",
            1024
        )

    @property
    def review_temperature(self) -> float:
        return self._data.get(
            "review",
            {}
        ).get(
            "temperature",
            0.2
        )

    @property
    def mock_ocr(self) -> bool:
        return os.getenv("MOCK_OCR", "false").lower() == "true"


cfg = Config(_load())