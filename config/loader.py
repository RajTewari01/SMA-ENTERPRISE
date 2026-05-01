"""
loader.py
=========
Environment-aware config loader. Returns DevConfig or ProdConfig
based on APP_ENV in the env file.
"""

from pathlib import Path

from dotenv import dotenv_values

from config.prod import ProdConfig
from config.dev import DevConfig

_ROOT_ = Path(__file__).absolute().resolve().parents[1]
_ENV_FILE = _ROOT_ / "env" / "config.env"

# Load env safely (None if file doesn't exist)
_env_data = dotenv_values(_ENV_FILE) if _ENV_FILE.exists() else {}


def get_config():
    """Return config based on APP_ENV environment variable."""
    env = _env_data.get("APP_ENV", "development")
    if env == "production":
        return ProdConfig()
    return DevConfig()