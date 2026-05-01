"""
Pexels Image Pipeline
======================
Factory function for downloading high-resolution stock images from Pexels.

>>> Registered via @register_pipeline decorator.
>>> Auto-discovered by discover_pipelines() at startup.
"""

from pathlib import Path
from typing import Literal, Optional

from .pipelines_types import ConfigPipelines, ApiTemplate, AuthType, PaginationType
from .registry import register_pipeline


@register_pipeline(
    name="pexels_image",
    keywords=["pexels", "stock", "photo", "image", "hd", "wallpaper", "high-res"],
    description="Pexels — a curated library for high-resolution stock photos.",
    media_type="image",
    api_calls_per_hour=200,
    d_exec=True,
)
def get_pexels_image_config(
    search_term: str,
    item_count: int = 25,
    output_dir: Optional[Path | str] = None,
    request_limit: int = 200,
    safe_search: Literal["off", "on"] = "off",
    debug: bool = False,
) -> ConfigPipelines:
    """
    Factory to create a ConfigPipelines for Pexels image downloads.
    """
    template = ApiTemplate(
        base_url="https://api.pexels.com/v1/search",
        auth_type=AuthType.BEARER,
        auth_key="PEXELS_API_KEY",
        search_param="query",
        pagination=PaginationType.PAGE,
        page_params="page",
        per_page_params="per_page",
        per_page_default=20,
    )

    return ConfigPipelines(
        safe_search=safe_search,
        search_term=search_term,
        media_type="images",
        debug=debug,
        count=item_count,
        output_dir=output_dir,
        req_limit=request_limit,
        api_provider="Pexels",
        template=template,
    )
