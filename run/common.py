"""Shared helpers: load .env and config/models.yaml."""

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    os.environ.setdefault("CYBENCH_ACKNOWLEDGE_RISKS", "1")


def load_config() -> dict:
    with open(ROOT / "config" / "models.yaml") as f:
        return yaml.safe_load(f)


def model_spec(key: str) -> tuple[str, dict]:
    """Return (inspect model string, model_args) for a key in models.yaml."""
    m = load_config()["models"][key]
    return m.get("inspect_model") or f"openai/{m['id']}", dict(m.get("model_args") or {})


def model_key_for(model_name: str) -> str | None:
    """Map an Inspect model name (e.g. 'openai/deepseek-v4-flash') back to its key."""
    for key, m in load_config()["models"].items():
        if model_name.endswith(m["id"]):
            return key
    return None
