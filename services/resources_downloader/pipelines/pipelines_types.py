from typing import List, Literal
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import random
import json
from sys import path
__ROOT__ = Path(__file__).absolute().resolve().parents[2]
from core.paths import DEBUG
from services.resources_downloader.pipelines.base import sanitize_search_term

path.insert(0,str())
class MediaTypes(str, Enum):
    SONGS = "songs"
    IMAGES = "images"
    VIDEOS = "videos"
    GIFS = "gifs"
    MUSIC = "music" 


class AuthType(str,Enum):
    HEADERS = "header"
    QUERY = "query"
    BEARER = "bearer"
    NONE = "none"

class PaginationType(str,Enum):
    NONE = "none"
    PAGE = "page"
    CURSOR = "cursor"
    OFFSET = "offset"


@dataclass
class ApiTemplate:
    base_url : str
    auth_type : AuthType
    auth_key : str
    auth_param : str = 'api_key'
    search_param : str = "q"
    pagination : PaginationType = PaginationType.NONE
    page_params : str = "page"
    per_page_params : str = "per_page"
    per_page_default : int = 20
    extra_params : dict = field(default_factory=dict)


@dataclass
class ConfigPipelines :
    safe_search : Literal['off','on'] = 'off'
    search_term : str | None = field(default=None)
    media_type : List[MediaTypes] = field(default_factory= lambda : list(MediaTypes.IMAGES))
    capture_logs : bool = True
    debug : bool = DEBUG
    count : int = None
    req_limit : int = None
    output_dir : Path | str | None = None
    api_provider : str = ''
    template : ApiTemplate | None = None

    def __post_init___(self):
        DEFAULT_MEDIA_COUNT = {
            "SONGS" : 1,
            "MUSIC" : 1,
            "IMAGES" : 20,
            "VIDEOS" : 5,
            "GIFS" : 10
        }
        if self.count is None:
            self.count = sum(DEFAULT_MEDIA_COUNT.get(mt.values.upper(),5)for mt in self.media_type)
        if self.output_dir:
            if not Path(self.output_dir).exists():
                self.output_dir.mkdir(parents=True,exist_ok =True)
        if self.search_term:
            self.search_term = self.sanitize_searchterm(term=self.search_term)

    def _sanitize_searchterm(self, term : str ) ->str :
        sanitized_term = sanitize_search_term(term=term)
        return sanitized_term 
        
    def next_searchterm() ->str : pass

    def get_random_searchterm1()->str : pass


    


