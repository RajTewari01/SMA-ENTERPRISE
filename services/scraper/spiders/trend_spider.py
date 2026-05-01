"""
trend_spider.py — Scrape trending topics from various sources.
"""
import scrapy
from typing import Any


class TrendSpider(scrapy.Spider):
    """Scrape trending topics from Google Trends and Twitter trending."""

    name = "trends"
    allowed_domains = ["trends.google.com"]
    start_urls = ["https://trends.google.com/trending?geo=US"]

    def __init__(self, country: str = "US", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [f"https://trends.google.com/trending?geo={country}"]

    def parse(self, response):
        for trend in response.css("div.feed-item"):
            title = trend.css("span.title::text").get()
            if title:
                yield {
                    "topic": title.strip(),
                    "source": "google_trends",
                    "url": response.url,
                }
