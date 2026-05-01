"""
hashtag_spider.py — Scrape hashtag performance data.
"""
import scrapy


class HashtagSpider(scrapy.Spider):
    """Scrape hashtag volume and related tags."""

    name = "hashtags"
    allowed_domains = ["best-hashtags.com"]

    def __init__(self, hashtag: str = "photography", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [f"https://best-hashtags.com/hashtag/{hashtag}/"]

    def parse(self, response):
        for tag_block in response.css("div.tag-box"):
            tags = tag_block.css("span::text").getall()
            for tag in tags:
                tag = tag.strip().lstrip("#")
                if tag:
                    yield {"hashtag": tag, "source": "best-hashtags"}
