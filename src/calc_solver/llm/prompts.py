from __future__ import annotations

from pathlib import Path
import yaml


_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        p = Path("configs/prompts.yaml")
        if not p.exists():
            p = Path(__file__).parent.parent.parent.parent / "configs" / "prompts.yaml"
        _cache = yaml.safe_load(p.read_text(encoding="utf-8"))
    return _cache


def get(section: str, key: str) -> str:
    data = _load()
    return data[section][key]


def format_prompt(section: str, key: str, **kwargs: object) -> str:
    template = get(section, key)
    return template.format(**kwargs)
