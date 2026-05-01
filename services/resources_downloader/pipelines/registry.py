"""
registry.py
===========
Central pipeline registry with decorator-based registration and auto-discovery.

Usage:
    from .registry import register_pipeline, discover_pipelines, get_pipeline

    @register_pipeline(name="my_pipeline", keywords=["example"], ...)
    def my_factory(...) -> ConfigPipelines:
        ...

    discover_pipelines()          # auto-imports all sibling pipeline modules
    config = get_pipeline("my_pipeline")(search_term="cats")
"""

import importlib
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class PipelineMeta:
    """Metadata attached to each registered pipeline."""
    name: str
    keywords: List[str]
    description: str
    media_type: str
    api_calls_per_hour: int = 0
    d_exec: bool = False


# ── internal store ──────────────────────────────────────────────
_REGISTRY: Dict[str, "RegisteredPipeline"] = {}


@dataclass
class RegisteredPipeline:
    meta: PipelineMeta
    factory: Callable


# ── decorator ───────────────────────────────────────────────────
def register_pipeline(
    name: str,
    keywords: List[str],
    description: str,
    media_type: str,
    api_calls_per_hour: int = 0,
    d_exec: bool = False,
):
    """Decorator that registers a factory function as a named pipeline."""
    def decorator(fn: Callable) -> Callable:
        meta = PipelineMeta(
            name=name,
            keywords=keywords,
            description=description,
            media_type=media_type,
            api_calls_per_hour=api_calls_per_hour,
            d_exec=d_exec,
        )
        _REGISTRY[name] = RegisteredPipeline(meta=meta, factory=fn)
        return fn
    return decorator


# ── lookup helpers ──────────────────────────────────────────────
def get_pipeline(name: str) -> Callable:
    """Return the factory function for a registered pipeline by name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Pipeline '{name}' not found. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name].factory


def get_pipeline_meta(name: str) -> PipelineMeta:
    """Return metadata for a registered pipeline."""
    return _REGISTRY[name].meta


def list_pipelines() -> Dict[str, PipelineMeta]:
    """Return all registered pipelines and their metadata."""
    return {name: rp.meta for name, rp in _REGISTRY.items()}


def search_pipelines(keyword: str) -> List[PipelineMeta]:
    """Find pipelines whose keywords match a search term."""
    keyword = keyword.lower()
    return [
        rp.meta for rp in _REGISTRY.values()
        if any(keyword in kw for kw in rp.meta.keywords)
    ]


# ── auto-discovery ──────────────────────────────────────────────
def discover_pipelines():
    """
    Import all Python modules in this package so that their
    @register_pipeline decorators fire and populate the registry.
    """
    package_dir = Path(__file__).resolve().parent
    package_name = __package__

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        importlib.import_module(f"{package_name}.{module_info.name}")
