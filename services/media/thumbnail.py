"""
thumbnail.py
============
Auto-generate thumbnails for YouTube/Instagram using Pillow.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

THUMBNAIL_SIZES = {
    "youtube": (1280, 720),
    "instagram": (1080, 1080),
    "tiktok": (1080, 1920),
}


class ThumbnailGenerator:
    """Generate eye-catching thumbnails with text overlays."""

    def __init__(
        self,
        size: Tuple[int, int] = (1280, 720),
        platform: str = "youtube",
    ):
        if platform in THUMBNAIL_SIZES:
            size = THUMBNAIL_SIZES[platform]
        self.width, self.height = size

    def generate(
        self,
        background_image: str | Path,
        title_text: str,
        output_path: str | Path = "thumbnail.jpg",
        subtitle_text: Optional[str] = None,
        darken: float = 0.4,
    ) -> Path:
        """
        Generate a thumbnail with text overlay.

        Args:
            background_image: Path to background image
            title_text: Main title text (large, bold)
            output_path: Where to save
            subtitle_text: Optional smaller text below title
            darken: Darken background (0=none, 1=black). Helps text readability.

        Returns:
            Path to generated thumbnail
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load and resize background
        bg = Image.open(background_image).convert("RGB")
        bg = self._cover_crop(bg)

        # Darken background
        if darken > 0:
            overlay = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            bg = Image.blend(bg, overlay, darken)

        draw = ImageDraw.Draw(bg)

        # Load fonts (fallback to default)
        try:
            title_font = ImageFont.truetype("arial.ttf", size=72)
            sub_font = ImageFont.truetype("arial.ttf", size=36)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

        # Draw title (centered, with shadow)
        title_text = title_text.upper()
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (self.width - text_w) // 2
        y = (self.height - text_h) // 2 - 30

        # Shadow
        draw.text((x + 3, y + 3), title_text, fill=(0, 0, 0), font=title_font)
        # Main text
        draw.text((x, y), title_text, fill=(255, 255, 255), font=title_font)

        # Subtitle
        if subtitle_text:
            sub_bbox = draw.textbbox((0, 0), subtitle_text, font=sub_font)
            sub_w = sub_bbox[2] - sub_bbox[0]
            sub_x = (self.width - sub_w) // 2
            sub_y = y + text_h + 20
            draw.text((sub_x, sub_y), subtitle_text, fill=(200, 200, 200), font=sub_font)

        bg.save(output_path, quality=95)
        logger.info("Thumbnail generated: %s", output_path)
        return output_path

    def _cover_crop(self, img: Image.Image) -> Image.Image:
        """Resize and center-crop to target dimensions."""
        img_ratio = img.width / img.height
        target_ratio = self.width / self.height

        if img_ratio > target_ratio:
            new_height = self.height
            new_width = int(self.height * img_ratio)
        else:
            new_width = self.width
            new_height = int(self.width / img_ratio)

        img = img.resize((new_width, new_height), Image.LANCZOS)

        left = (new_width - self.width) // 2
        top = (new_height - self.height) // 2
        return img.crop((left, top, left + self.width, top + self.height))
