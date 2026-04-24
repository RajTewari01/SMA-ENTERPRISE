# ================== PROJECT ROOT =====================
import platform
import sys
import warnings
from pathlib import Path
from typing import Dict, Literal, Tuple, cast, Any

__ROOT__ = Path(__file__).absolute().resolve().parents[1]
sys.path.insert(0, str(__ROOT__))
from config import config

APP_ENVIRONMENT = config.CONFIG_TYPE
DEBUG = config.DEBUG

CONFIG_ENVIRONMENT = __ROOT__/"config.env"
