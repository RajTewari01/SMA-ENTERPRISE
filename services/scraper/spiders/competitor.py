"""
competitor.py — Scrape competitor social media profiles for analysis.
"""
import scrapy


class CompetitorSpider(scrapy.Spider):
    """Scrape public profile data for competitive analysis."""

    name = "competitor"

    def __init__(self, url: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if url:
            self.start_urls = [url]

    def parse(self, response):
        yield {
            "url": response.url,
            "title": response.css("title::text").get("").strip(),
            "description": response.css("meta[name=description]::attr(content)").get(""),
            "headings": response.css("h1::text, h2::text").getall(),
            "links_count": len(response.css("a::attr(href)").getall()),
            "images_count": len(response.css("img::attr(src)").getall()),
        }
