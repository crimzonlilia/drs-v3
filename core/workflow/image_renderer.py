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
    py_max: int,
    bubble_type: str = "normal"
) -> None:
    """
    Function for background masking.
    Uses 0.95 scale mapping to clean up 100% of Japanese text near margins.
    Uses rectangular masking for narration and scream types, elliptical for others.
    """
    draw = ImageDraw.Draw(img)
    box_w = px_max - px_min
    box_h = py_max - py_min
    center_x = px_min + box_w / 2
    center_y = py_min + box_h / 2
    
    scaled_w = box_w * 0.95
    scaled_h = box_h * 0.95
    
    coords = [
        center_x - scaled_w / 2,
        center_y - scaled_h / 2,
        center_x + scaled_w / 2,
        center_y + scaled_h / 2
    ]
    
    if bubble_type in ("narration", "scream"):
        draw.rectangle(coords, fill="white")
    else:
        draw.ellipse(coords, fill="white")


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


def wrap_ellipse(
    words: list[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    box_w: float,
    box_h: float,
    line_height: float,
    scale: float = 0.72
) -> list[str] | None:
    """
    Wrap words into lines dynamically fitting within an ellipse shape.
    Calculates vertical offset and allowed horizontal width for each line.
    """
    import math
    # Use the scaled semi-axes so the text ellipse is geometrically consistent
    # with the 70% fill constraint applied in both axes
    a = box_w * scale / 2.0  # horizontal semi-axis of the text ellipse
    b = box_h * scale / 2.0  # vertical semi-axis of the text ellipse
    if b <= 0:
        return None
        
    num_words = len(words)
    if num_words == 0:
        return []

    # Try to wrap in N lines, from 1 to 15
    for N in range(1, 16):
        total_h = N * line_height
        if total_h > box_h * scale:
            continue
            
        allowed_widths = []
        valid_n = True
        for i in range(N):
            y_i = (i - (N - 1) / 2.0) * line_height
            ratio = y_i / b
            if abs(ratio) >= 1.0:
                valid_n = False
                break
            # Width at this row = chord of the text ellipse at height y_i
            allowed_widths.append(2.0 * a * math.sqrt(1.0 - ratio * ratio))
            
        if not valid_n:
            continue
            
        lines = []
        word_idx = 0
        
        for line_limit in allowed_widths:
            if word_idx >= num_words:
                break
                
            curr_line = [words[word_idx]]
            word_idx += 1
            
            while word_idx < num_words:
                next_word = words[word_idx]
                test_line = " ".join(curr_line + [next_word])
                try:
                    line_w = font.getlength(test_line)
                except AttributeError:
                    try:
                        line_w = font.getmask(test_line).size[0]
                    except Exception:
                        line_w = len(test_line) * (font.size * 0.6 if hasattr(font, 'size') else 8)
                        
                if line_w <= line_limit:
                    curr_line.append(next_word)
                    word_idx += 1
                else:
                    break
            lines.append(" ".join(curr_line))
            
        if word_idx == num_words:
            return lines
            
    return None


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
        
        bubble_type = getattr(b, 'bubble_type', 'normal')
        
        # 1. Clean the original text block area
        mask_original_text_block_background(img, px_min, py_min, px_max, py_max, bubble_type)
        
        # 2. Determine font size dynamically using auto-scaling
        words = b.translated_text.split()
        if not words:
            continue
            
        is_oval = bubble_type in ('normal', 'thought')
        font_size = 24  # Start with comfortable max size
        font = None
        lines = []
        line_height = 20
        
        while font_size >= 9:
            font = get_vietnamese_font(font_size, bubble_type)
            try:
                line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 4
            except AttributeError:
                line_height = font.size + 4 if hasattr(font, 'size') else 20
                
            if is_oval:
                res = wrap_ellipse(words, font, box_w, box_h, line_height, scale=0.72)
                if res is not None:
                    lines = res
                    break
            else:
                max_text_w = box_w * 0.72
                res_lines = wrap_text(b.translated_text, font, max_text_w)
                total_text_h = len(res_lines) * line_height
                if total_text_h <= box_h * 0.72:
                    lines = res_lines
                    break
            font_size -= 1
            
        if not lines:
            # Heuristic fallback if it doesn't fit
            font_size = 9
            font = get_vietnamese_font(font_size, bubble_type)
            try:
                line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 4
            except AttributeError:
                line_height = font.size + 4 if hasattr(font, 'size') else 20
            lines = wrap_text(b.translated_text, font, box_w * 0.85)
            
        # 3. Calculate vertical alignment with dynamic line spacing
        extra_spacing = 0
        if len(lines) > 1:
            leftover_h = (box_h * 0.72) - (len(lines) * line_height)
            if leftover_h > 0:
                # Distribute extra spacing evenly between lines, capped at 40% of line height
                extra_spacing = min(line_height * 0.4, leftover_h / (len(lines) - 1))
                
        total_text_h = len(lines) * line_height + (len(lines) - 1) * extra_spacing
        start_y = py_min + (box_h - total_text_h) / 2
        
        # 4. Draw each line centered horizontally
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
                (start_x, start_y + i * (line_height + extra_spacing)),
                line,
                font=font,
                fill="black"
            )

    # Export to bytes
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    return out_buf.getvalue()
