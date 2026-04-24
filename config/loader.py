from config.prod import ProdConfig
from config.dev import DevConfig
from pathlib import Path
from dotenv import dotenv_values
from typing import Callable,Any
import sys

__ROOT__ =  Path(__file__).absolute().resolve().parents[1]
sys.path.insert(0,str(__ROOT__))
from core.paths import APP_ENVIRONMENT

env_data = dotenv_values(APP_ENVIRONMENT) if Path(APP_ENVIRONMENT).exists() else None


def get_config() -> Callable[..., Any]:
    env_values = env_data.get("APP_ENV","development")
    if env_values == 'production': 
        return ProdConfig()
    return DevConfig()    