"""
Image Renderer — utility to mask original source text layouts and render target text on screenshots or pages.
"""

from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from core.agents.layout_translator import LayoutTextBlock


def get_vietnamese_font(font_size: int = 16, bubble_type: str = "normal") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Attempt to load a standard Windows font that matches the block type and supports Vietnamese.
    """
    # Map layout block/bubble types to preferred Windows ttf files
    type_font_map = {
        "thought": [
            "C:\\Windows\\Fonts\\calibrii.ttf",   # Calibri Italic
            "C:\\Windows\\Fonts\\ariali.ttf",     # Arial Italic
        ],
        "scream": [
            "C:\\Windows\\Fonts\\ariblk.ttf",     # Arial Black
            "C:\\Windows\\Fonts\\arialbd.ttf",    # Arial Bold
            "C:\\Windows\\Fonts\\comicbd.ttf",    # Comic Sans MS Bold
        ],
        "narration": [
            "C:\\Windows\\Fonts\\times.ttf",      # Times New Roman Regular
            "C:\\Windows\\Fonts\\calibri.ttf",    # Calibri Regular
        ],
        "normal": [
            "C:\\Windows\\Fonts\\comic.ttf",      # Comic Sans MS
            "C:\\Windows\\Fonts\\calibri.ttf",    # Calibri Regular
            "C:\\Windows\\Fonts\\arial.ttf",      # Arial Regular
        ]
    }
    
    preferred_paths = type_font_map.get(bubble_type, type_font_map["normal"])
    # Fallback paths if preferred not found
    fallback_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    
    for path in (preferred_paths + fallback_paths):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                pass
    
    return ImageFont.load_default()


def mask_original_text_block_background(
    img: Image.Image,
    px_min: int,
    py_min: int,
    px_max: int,
    py_max: int
) -> None:
    """
    Function for background masking.
    Currently it uses standard masking (solid white ellipse inside boundaries).
    Later, we can integrate OpenCV inpainting or LaMa-based models here.
    """
    draw = ImageDraw.Draw(img)
    inset = 3
    draw.ellipse(
        [px_min + inset, py_min + inset, px_max - inset, py_max - inset],
        fill="white"
    )


def wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: float) -> list[str]:
    """
    Wrap words into lines so they don't exceed max_width in pixels.
    """
    words = text.split()
    if not words:
        return []
        
    # Helper to calculate text width
    def get_word_width(w_str: str) -> float:
        try:
            return font.getlength(w_str)
        except AttributeError:
            try:
                return font.getmask(w_str).size[0]
            except Exception:
                return len(w_str) * (font.size * 0.6 if hasattr(font, 'size') else 8)

    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        w = get_word_width(test_line)
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines


def render_image_layout_page(
    image_bytes: bytes,
    blocks: list[LayoutTextBlock],
) -> bytes:
    """
    Draw solid white masks over original text regions and render wrapped Vietnamese text inside them.
    Only touches text regions specified by bounding boxes, protecting the rest of the image.
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
        
    width, height = img.size
    draw = ImageDraw.Draw(img)

    for b in blocks:
        x_min, y_min, x_max, y_max = b.box
        
        # Denormalize coordinates (0-1000 to actual pixels)
        px_min = int(x_min * width / 1000)
        py_min = int(y_min * height / 1000)
        px_max = int(x_max * width / 1000)
        py_max = int(y_max * height / 1000)
        
        box_w = px_max - px_min
        box_h = py_max - py_min
        
        # 1. Clean the original text block area
        mask_original_text_block_background(img, px_min, py_min, px_max, py_max)
        
        # 2. Determine font size based on block size
        font_size = max(11, min(24, int(box_w / 8)))
        font = get_vietnamese_font(font_size, getattr(b, 'bubble_type', 'normal'))
        
        # Wrap text (leave margin inside block)
        margin = max(10, int(box_w * 0.15))
        max_text_w = box_w - (margin * 2)
        lines = wrap_text(b.translated_text, font, max_text_w)
        
        # Calculate vertical centering
        try:
            line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 4
        except AttributeError:
            line_height = font.size + 4 if hasattr(font, 'size') else 20
            
        total_text_h = len(lines) * line_height
        start_y = py_min + (box_h - total_text_h) / 2
        
        # Draw each line centered horizontally
        for i, line in enumerate(lines):
            try:
                line_w = font.getlength(line)
            except AttributeError:
                try:
                    line_w = font.getmask(line).size[0]
                except Exception:
                    line_w = len(line) * (font.size * 0.6 if hasattr(font, 'size') else 8)
                    
            start_x = px_min + (box_w - line_w) / 2
            draw.text(
                (start_x, start_y + i * line_height),
                line,
                font=font,
                fill="black"
            )

    # Export to bytes
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    return out_buf.getvalue()
