"""
engine.py
=========
Download engine that consumes a ConfigPipelines + ApiTemplate to execute
HTTP-based media downloads with auth, pagination, and file persistence.

Supports both synchronous and async (Celery) execution modes via a
progress callback interface.

Usage (sync):
    from services.resources_downloader.engine import DownloadEngine

    config = get_pexels_image_config(search_term="mountains")
    engine = DownloadEngine(config)
    results = engine.run()

Usage (celery):
    from services.resources_downloader.tasks import download_task
    result = download_task.delay("pexels_image", search_term="mountains")
"""

import os
import time
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from services.resources_downloader.pipelines.pipelines_types import (
    AuthType,
    ConfigPipelines,
    ApiTemplate,
    PaginationType,
)

logger = logging.getLogger(__name__)


# ── progress callback type ──────────────────────────────────────
# Signature: (current: int, total: int, status: str, meta: dict) -> None
ProgressCallback = Callable[[int, int, str, Dict[str, Any]], None]


def _noop_progress(current: int, total: int, status: str, meta: Dict) -> None:
    """Default no-op progress callback for synchronous runs."""
    pass


class DownloadEngine:
    """
    Engine that takes a fully populated ConfigPipelines,
    reads its ApiTemplate, and drives the download loop:

        build_headers() → build_params() → fetch_page() → extract_urls() → download_file()
                                              ↑                                    |
                                              └──── paginate ◄─────────────────────┘

    Progress reporting:
        Pass a `on_progress` callback to `run()` for Celery or any other
        system that needs live updates. The callback receives:
            (current_count, total_target, status_string, metadata_dict)
    """

    def __init__(self, config: ConfigPipelines):
        self.config = config
        self.template: ApiTemplate = config.template
        self._api_key: str = self._load_api_key()
        self._client = httpx.Client(timeout=30.0)
        self._downloaded: int = 0
        self._failed: int = 0

        # Ensure output directory
        if self.config.output_dir:
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    # ── auth ────────────────────────────────────────────────────
    def _load_api_key(self) -> str:
        """Load the API key from environment using the template's auth_key as the env var name."""
        if self.template.auth_type == AuthType.NONE:
            return ""
        key = os.getenv(self.template.auth_key, "")
        if not key:
            raise EnvironmentError(
                f"Missing env var '{self.template.auth_key}'. "
                f"Set it in your .env or environment."
            )
        return key

    def _build_headers(self) -> Dict[str, str]:
        """Construct auth headers based on AuthType."""
        headers = {"User-Agent": "SMA-Enterprise/1.0"}

        if self.template.auth_type == AuthType.BEARER:
            headers["Authorization"] = self._api_key
        elif self.template.auth_type == AuthType.HEADERS:
            headers[self.template.auth_param] = self._api_key

        return headers

    # ── params & pagination ─────────────────────────────────────
    def _build_params(self, page: Any = 1) -> Dict[str, Any]:
        """Build query parameters including search, pagination, and extras."""
        params: Dict[str, Any] = {
            self.template.search_param: self.config.search_term,
        }

        # Auth via query string (e.g. ?api_key=xxx)
        if self.template.auth_type == AuthType.QUERY:
            params[self.template.auth_param] = self._api_key

        # Pagination
        if self.template.pagination == PaginationType.PAGE:
            params[self.template.page_params] = page
            params[self.template.per_page_params] = self.template.per_page_default
        elif self.template.pagination == PaginationType.OFFSET:
            params[self.template.page_params] = (page - 1) * self.template.per_page_default
            params[self.template.per_page_params] = self.template.per_page_default
        elif self.template.pagination == PaginationType.CURSOR:
            if page != 1:  # first request has no cursor
                params[self.template.page_params] = page

        # Any extra params the template defines
        params.update(self.template.extra_params)

        return params

    def _get_next_page(self, page: Any, response_data: Dict) -> Optional[Any]:
        """Determine the next page/cursor, or None if done."""
        if self.template.pagination == PaginationType.NONE:
            return None
        if self.template.pagination == PaginationType.CURSOR:
            next_cursor = (
                response_data.get("next_page")
                or response_data.get("next_cursor")
                or response_data.get("continuation_token")
            )
            return next_cursor  # None means no more results
        # page / offset based — check if we got fewer results than expected
        return page + 1

    # ── HTTP & extraction ───────────────────────────────────────
    def _fetch_page(self, page: Any = 1) -> Dict:
        """Make a single API request and return the JSON response."""
        headers = self._build_headers()
        params = self._build_params(page)

        if self.config.debug:
            logger.debug("GET %s params=%s", self.template.base_url, params)

        resp = self._client.get(
            self.template.base_url,
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def _extract_urls(self, data: Dict) -> List[str]:
        """
        Extract downloadable media URLs from an API response.

        Override this for non-standard API shapes. Default implementation
        handles common patterns (Pexels, Pixabay, Unsplash-like).
        """
        urls: List[str] = []

        # Pexels-style: { "photos": [ { "src": { "original": "..." } } ] }
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            url = src.get("original") or src.get("large2x") or src.get("large")
            if url:
                urls.append(url)

        # Pixabay-style: { "hits": [ { "largeImageURL": "..." } ] }
        for hit in data.get("hits", []):
            url = hit.get("largeImageURL") or hit.get("webformatURL")
            if url:
                urls.append(url)

        # Generic fallback: look for a "results" or "data" list with "url" fields
        for item in data.get("results", data.get("data", [])):
            if isinstance(item, dict):
                url = item.get("url") or item.get("download_url")
                if url:
                    urls.append(url)

        return urls

    # ── download ────────────────────────────────────────────────
    def _download_file(self, url: str, index: int) -> Optional[Path]:
        """Download a single file to the output directory."""
        output_dir = Path(self.config.output_dir or ".")
        ext = Path(url.split("?")[0]).suffix or ".jpg"
        filename = f"{self.config.search_term}_{index:04d}{ext}"
        filepath = output_dir / filename

        try:
            with self._client.stream("GET", url) as stream:
                stream.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            if self.config.debug:
                logger.debug("Saved %s", filepath)
            return filepath
        except httpx.HTTPError as e:
            logger.warning("Failed to download %s: %s", url, e)
            self._failed += 1
            return None

    # ── retry with backoff ──────────────────────────────────────
    def _fetch_page_with_retry(self, page: Any, max_retries: int = 3) -> Optional[Dict]:
        """Fetch a page with exponential backoff on rate-limit (429) errors."""
        for attempt in range(max_retries):
            try:
                return self._fetch_page(page)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited — back off exponentially
                    wait = 2 ** attempt * 5  # 5s, 10s, 20s
                    logger.warning(
                        "Rate limited (429). Retrying in %ds (attempt %d/%d)",
                        wait, attempt + 1, max_retries,
                    )
                    time.sleep(wait)
                else:
                    raise
        logger.error("Max retries exceeded for page %s", page)
        return None

    # ── main loop ───────────────────────────────────────────────
    def run(self, on_progress: Optional[ProgressCallback] = None) -> List[Path]:
        """
        Execute the full download pipeline:
        paginate → extract URLs → download files → stop at count or req_limit.

        Args:
            on_progress: Optional callback for progress reporting.
                         Celery tasks pass `self.update_state` here.
                         Signature: (current, total, status, meta) -> None
        """
        progress = on_progress or _noop_progress
        downloaded_paths: List[Path] = []
        page: Any = 1
        requests_made = 0
        target = self.config.count or 25

        logger.info(
            "Starting %s download: query='%s', target=%d",
            self.config.api_provider,
            self.config.search_term,
            target,
        )

        progress(0, target, "STARTED", {
            "provider": self.config.api_provider,
            "query": self.config.search_term,
        })

        while len(downloaded_paths) < target:
            # Rate limit guard
            if self.config.req_limit and requests_made >= self.config.req_limit:
                logger.warning("Request limit (%d) reached.", self.config.req_limit)
                progress(len(downloaded_paths), target, "RATE_LIMITED", {
                    "requests_made": requests_made,
                })
                break

            data = self._fetch_page_with_retry(page)
            requests_made += 1

            if data is None:
                logger.error("Failed to fetch page %s after retries.", page)
                break

            urls = self._extract_urls(data)
            if not urls:
                logger.info("No more results on page %s.", page)
                break

            for url in urls:
                if len(downloaded_paths) >= target:
                    break
                path = self._download_file(url, len(downloaded_paths) + 1)
                if path:
                    downloaded_paths.append(path)
                    # Report progress after each file
                    progress(len(downloaded_paths), target, "DOWNLOADING", {
                        "file": str(path),
                        "requests_made": requests_made,
                        "failed": self._failed,
                    })

            page = self._get_next_page(page, data)
            if page is None:
                break

        status = "SUCCESS" if len(downloaded_paths) >= target else "PARTIAL"
        logger.info(
            "Done. Downloaded %d/%d files (%d API requests, %d failed).",
            len(downloaded_paths),
            target,
            requests_made,
            self._failed,
        )

        progress(len(downloaded_paths), target, status, {
            "requests_made": requests_made,
            "failed": self._failed,
            "files": [str(p) for p in downloaded_paths],
        })

        self._client.close()
        return downloaded_paths
