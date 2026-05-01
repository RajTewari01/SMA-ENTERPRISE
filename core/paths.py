# ================== PROJECT ROOT =====================
import warnings
import traceback
from typing import List
import platform
import sys
import warnings
from pathlib import Path
from typing import Dict, Literal, Tuple, cast, Any

__ROOT__ = Path(__file__).absolute().resolve().parents[1]
sys.path.insert(0, str(__ROOT__))
from config import config

# ================== APP CONFIG =====================

APP_ENVIRONMENT:str = config.CONFIG_TYPE
DEBUG:bool = config.DEBUG

# ================== DIRECTORY PATHS =====================

ASSETS_DIR:Path = __ROOT__/"assets"
CONFIG_DIR:Path = __ROOT__/"config"
DOCKER_DIR:Path = __ROOT__/"docker"
DATA_DIR:Path = __ROOT__/"data"
ENV_DIR:Path = __ROOT__/"env"
DB_DIR:Path = __ROOT__/"db"

# ================== ALL DATABASE PATHS ===================
ALL_DATABASE_PATH : Dict[str,Path] = {
    "STORIES" : DATA_DIR/"stories.db"
}

CONFIG_ENVIRONMENT : Path = __ROOT__/"config.env"


class Paths:
    def __init__(self,root:Path=__ROOT__):
        self.__root__ = root
        self.assets_dir = self.__root__ / "assets"
        self.config_dir = self.__root__ / "config"
        self.docker_dir = self.__root__ / "docker"
        self.data_dir = self.__root__ / "data"
        self.env_dir = self.__root__ / "env"
        self.db_dir = self.__root__ / "db"

    def get_all_database_paths(self) -> Dict[str, Path]:
        return {
            "STORIES" : self.data_dir / "stories.db"
        }

    def ensure_dirs(abs_path : Path | str, debug : bool = DEBUG):
        if isinstance(abs_path, str):abs_path = Path(abs_path)
        if not abs_path.exists(): 
            try: abs_path.mkdir(parents=True,exist_ok=True)
            except Exception as e:
                if debug:
                    import traceback
                    traceback.print_exception(e)
                else: print(warnings.warn(e))




        