from pathlib import Path

_ROOT_ = Path(__file__).parent.parent

class BaseConfig:
    ASSETS_DIR = _ROOT_ / "assets"
    LLM_DIR = _ROOT_ / "models"
    D_EXEC = False
    IMMEDIATE_EXEC = False
    IMMEDIATE_ERROR_VALIDATION = False
    