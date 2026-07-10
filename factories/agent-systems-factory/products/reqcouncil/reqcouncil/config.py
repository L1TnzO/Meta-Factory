"""Repo config as DATA (docs/design/03 §3): models.yml + thresholds.yml under config/.

Changing these files requires a written reason (repo rule) — code only READS them.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"


def load_models(config_dir: Path | None = None) -> dict:
    """Parsed config/models.yml (foundation_model + judge sections)."""
    path = (config_dir or CONFIG_DIR) / "models.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_council(config_dir: Path | None = None) -> dict:
    """Parsed config/council.yml (protocol knobs: analysts, temps, tau_dup, band)."""
    path = (config_dir or CONFIG_DIR) / "council.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_thresholds(config_dir: Path | None = None) -> dict:
    """Parsed config/thresholds.yml (the blocking gates)."""
    path = (config_dir or CONFIG_DIR) / "thresholds.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader: KEY=VALUE lines -> os.environ, never overriding real env."""
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def api_key_from_env(env_var: str) -> str:
    """Resolve an API key by env-var name, falling back to the repo .env file."""
    if env_var not in os.environ:
        load_dotenv()
    key = os.environ.get(env_var, "")
    if not key:
        raise RuntimeError(
            f"{env_var} not set (checked environment and {REPO_ROOT / '.env'})"
        )
    return key
