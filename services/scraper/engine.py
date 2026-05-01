"""
engine.py — Scrapy runner for executing spiders from within the application.
"""
import logging
from typing import Any, Dict, List, Optional
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

logger = logging.getLogger(__name__)

# Default Scrapy settings
SCRAPY_SETTINGS = {
    "BOT_NAME": "sma_enterprise",
    "ROBOTSTXT_OBEY": True,
    "CONCURRENT_REQUESTS": 8,
    "DOWNLOAD_DELAY": 1.5,
    "USER_AGENT": "SMA-Enterprise/1.0 (+https://github.com/sma-enterprise)",
    "FEEDS": {},  # set per-run
    "LOG_LEVEL": "WARNING",
    "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
}


class ScraperEngine:
    """Run Scrapy spiders programmatically."""

    def __init__(self, settings: Optional[Dict] = None):
        self.settings = {**SCRAPY_SETTINGS, **(settings or {})}

    def run_spider(self, spider_cls, output_path: Optional[str] = None, **kwargs):
        """Run a spider and optionally save results to JSON."""
        settings = dict(self.settings)
        if output_path:
            settings["FEEDS"] = {output_path: {"format": "json", "overwrite": True}}

        process = CrawlerProcess(settings=settings)
        process.crawl(spider_cls, **kwargs)
        process.start(stop_after_crawl=True)
        logger.info("Spider %s completed", spider_cls.name)
