import io
import json
import logging
import re
from PIL import Image, ImageDraw, ImageFont
from core.utils.r2 import read_binary

logger = logging.getLogger(__name__)

def wrap_text_to_lines(draw: ImageDraw.ImageDraw, text: str, width: int, font: ImageFont.ImageFont) -> list:
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        try:
            line_w = draw.textlength(line_str, font=font)
        except Exception:
            try:
                line_w = font.getbbox(line_str)[2]
            except Exception:
                line_w = len(line_str) * 8 # Fallback
            
        if line_w > width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                # Single word is wider than the width, let it be on its own line
                lines.append(word)
                current_line = []
            
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def get_font_line_height(font: ImageFont.ImageFont) -> int:
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent
    except Exception:
        try:
            bbox = font.getbbox("X")
            return bbox[3] - bbox[1]
        except Exception:
            return 16

def get_text_height(lines: list, font: ImageFont.ImageFont) -> int:
    if not lines:
        return 0
    lh = get_font_line_height(font)
    return len(lines) * lh + (len(lines) - 1) * 2

def load_font_at_size(font_name: str, font_bytes: bytes, size: int) -> ImageFont.ImageFont:
    if font_bytes:
        try:
            return ImageFont.truetype(io.BytesIO(font_bytes), size)
        except Exception as e:
            logger.error(f"Failed to load custom font {font_name} from bytes: {e}")
            
    defaults = ["Arial", "Georgia", "Times New Roman", "Courier New", "Impact", "Noto Sans", "Noto Sans JP", "Noto Serif"]
    try:
        return ImageFont.truetype(font_name.lower() + ".ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

def find_optimal_font_size(
    draw: ImageDraw.ImageDraw, 
    text: str, 
    width: int, 
    height: int, 
    font_name: str, 
    font_bytes: bytes, 
    max_size: int
) -> tuple[ImageFont.ImageFont, int]:
    size = max_size
    min_size = 9
    
    while size >= min_size:
        font = load_font_at_size(font_name, font_bytes, size)
        lines = wrap_text_to_lines(draw, text, width, font)
        total_height = get_text_height(lines, font)
        
        fits = True
        if total_height > height:
            fits = False
        else:
            for l in lines:
                try:
                    line_w = draw.textlength(l, font=font)
                except Exception:
                    try:
                        line_w = font.getbbox(l)[2]
                    except Exception:
                        line_w = len(l) * (size * 0.5)
                if line_w > width:
                    fits = False
                    break
        
        if fits:
            return font, size
        size -= 1
        
    return load_font_at_size(font_name, font_bytes, min_size), min_size

class TextUnit:
    def __init__(self, text: str, ruby: str | None = None):
        self.text = text
        self.ruby = ruby

def parse_text_into_units(text: str) -> list[TextUnit]:
    units = []
    # Match either non-whitespace ending with [ruby] or plain non-whitespace
    for part in re.findall(r'\S+?\[[^\]]+\]|\S+', text):
        if '[' in part and part.endswith(']'):
            idx = part.find('[')
            base = part[:idx]
            ruby = part[idx+1:-1]
            units.append(TextUnit(text=base, ruby=ruby))
        else:
            units.append(TextUnit(text=part))
    return units

def get_unit_width(draw: ImageDraw.ImageDraw, unit: TextUnit, font: ImageFont.ImageFont, ruby_font: ImageFont.ImageFont) -> float:
    try:
        main_w = draw.textlength(unit.text, font=font)
    except Exception:
        try:
            main_w = font.getbbox(unit.text)[2]
        except Exception:
            main_w = len(unit.text) * 8
            
    if not unit.ruby:
        return main_w
        
    try:
        ruby_w = draw.textlength(unit.ruby, font=ruby_font)
    except Exception:
        try:
            ruby_w = ruby_font.getbbox(unit.ruby)[2]
        except Exception:
            ruby_w = len(unit.ruby) * 4
            
    return max(main_w, ruby_w)

def wrap_units_to_lines(draw: ImageDraw.ImageDraw, units: list[TextUnit], width: int, font: ImageFont.ImageFont, ruby_font: ImageFont.ImageFont) -> list[list[TextUnit]]:
    lines = []
    current_line = []
    current_line_w = 0
    
    for unit in units:
        unit_w = get_unit_width(draw, unit, font, ruby_font)
        try:
            space_w = draw.textlength(" ", font=font) if current_line else 0
        except Exception:
            space_w = 4 if current_line else 0
            
        if current_line_w + space_w + unit_w > width:
            if current_line:
                lines.append(current_line)
                current_line = [unit]
                current_line_w = unit_w
            else:
                lines.append([unit])
                current_line = []
                current_line_w = 0
        else:
            current_line.append(unit)
            current_line_w += space_w + unit_w
            
    if current_line:
        lines.append(current_line)
    return lines

def get_line_height(line: list[TextUnit], font: ImageFont.ImageFont, ruby_font: ImageFont.ImageFont) -> int:
    main_h = get_font_line_height(font)
    has_ruby = any(u.ruby for u in line)
    if has_ruby:
        ruby_h = get_font_line_height(ruby_font)
        return main_h + ruby_h + 2
    return main_h

def get_total_height_of_lines(lines: list[list[TextUnit]], font: ImageFont.ImageFont, ruby_font: ImageFont.ImageFont) -> int:
    if not lines:
        return 0
    total = 0
    for i, line in enumerate(lines):
        total += get_line_height(line, font, ruby_font)
        if i > 0:
            has_ruby = any(u.ruby for u in line) or any(u.ruby for u in lines[i-1])
            total += 8 if has_ruby else 4
    return total

def get_line_display_width(draw: ImageDraw.ImageDraw, line: list[TextUnit], font: ImageFont.ImageFont, ruby_font: ImageFont.ImageFont) -> float:
    if not line:
        return 0
    total_w = 0
    for i, unit in enumerate(line):
        if i > 0:
            try:
                total_w += draw.textlength(" ", font=font)
            except Exception:
                total_w += 4
        total_w += get_unit_width(draw, unit, font, ruby_font)
    return total_w

def find_optimal_font_size_for_ruby(
    draw: ImageDraw.ImageDraw, 
    units: list[TextUnit], 
    width: int, 
    height: int, 
    font_name: str, 
    font_bytes: bytes, 
    max_size: int
) -> tuple[ImageFont.ImageFont, ImageFont.ImageFont, int]:
    size = max_size
    min_size = 9
    
    while size >= min_size:
        font = load_font_at_size(font_name, font_bytes, size)
        ruby_size = max(8, int(size * 0.45))
        ruby_font = load_font_at_size(font_name, font_bytes, ruby_size)
        
        lines = wrap_units_to_lines(draw, units, width, font, ruby_font)
        total_height = get_total_height_of_lines(lines, font, ruby_font)
        
        fits = True
        if total_height > height:
            fits = False
        else:
            for line in lines:
                line_w = get_line_display_width(draw, line, font, ruby_font)
                if line_w > width:
                    fits = False
                    break
        
        if fits:
            return font, ruby_font, size
        size -= 1
        
    font = load_font_at_size(font_name, font_bytes, min_size)
    ruby_font = load_font_at_size(font_name, font_bytes, max(8, int(min_size * 0.45)))
    return font, ruby_font, min_size

def draw_text_wrapped(
    draw: ImageDraw.ImageDraw, 
    text: str, 
    box: list, 
    font_name: str, 
    font_bytes: bytes, 
    initial_size: int, 
    fill_color=(0, 0, 0)
):
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    
    # Apply padding to prevent text clipping at speech bubble edges (12% padding)
    pad_x = max(2, int(width * 0.12))
    pad_y = max(2, int(height * 0.12))
    
    x1_pad = x1 + pad_x
    y1_pad = y1 + pad_y
    x2_pad = x2 - pad_x
    y2_pad = y2 - pad_y
    
    width_pad = x2_pad - x1_pad
    height_pad = y2_pad - y1_pad
    
    max_size = max(initial_size, 28)
    
    # Check if text contains ruby markup
    if '[' in text:
        units = parse_text_into_units(text)
        font, ruby_font, optimal_size = find_optimal_font_size_for_ruby(draw, units, width_pad, height_pad, font_name, font_bytes, max_size)
        lines = wrap_units_to_lines(draw, units, width_pad, font, ruby_font)
        total_text_height = get_total_height_of_lines(lines, font, ruby_font)
        y = y1_pad + (height_pad - total_text_height) / 2
        
        try:
            ruby_h = ruby_font.getbbox("X")[3] - ruby_font.getbbox("X")[1]
        except Exception:
            ruby_h = 8
            
        for idx, line in enumerate(lines):
            if idx > 0:
                has_ruby = any(u.ruby for u in line) or any(u.ruby for u in lines[idx-1])
                y += 8 if has_ruby else 4
                
            line_w = get_line_display_width(draw, line, font, ruby_font)
            x = x1_pad + (width_pad - line_w) / 2
            
            has_line_ruby = any(u.ruby for u in line)
            line_h = get_line_height(line, font, ruby_font)
            
            for i, unit in enumerate(line):
                if i > 0:
                    try:
                        space_w = draw.textlength(" ", font=font)
                    except Exception:
                        space_w = 4
                    x += space_w
                    
                unit_w = get_unit_width(draw, unit, font, ruby_font)
                
                try:
                    main_w = draw.textlength(unit.text, font=font)
                except Exception:
                    try:
                        main_w = font.getbbox(unit.text)[2]
                    except Exception:
                        main_w = len(unit.text) * (optimal_size * 0.5)
                        
                # Center main text within unit_w
                main_x = x + (unit_w - main_w) / 2
                main_y = y
                if has_line_ruby:
                    main_y += ruby_h + 2
                    
                draw.text((main_x, main_y), unit.text, font=font, fill=fill_color)
                
                if unit.ruby:
                    try:
                        ruby_w = draw.textlength(unit.ruby, font=ruby_font)
                    except Exception:
                        try:
                            ruby_w = ruby_font.getbbox(unit.ruby)[2]
                        except Exception:
                            ruby_w = len(unit.ruby) * (max(8, int(optimal_size * 0.45)) * 0.5)
                    # Center ruby text within unit_w
                    ruby_x = x + (unit_w - ruby_w) / 2
                    draw.text((ruby_x, y), unit.ruby, font=ruby_font, fill=fill_color)
                    
                x += unit_w
                
            y += line_h
        return
        
    # Fallback to standard wrapping if no ruby markup is present
    font, optimal_size = find_optimal_font_size(draw, text, width_pad, height_pad, font_name, font_bytes, max_size)
    lines = wrap_text_to_lines(draw, text, width_pad, font)
    total_text_height = get_text_height(lines, font)
    
    lh = get_font_line_height(font)
    y = y1_pad + (height_pad - total_text_height) / 2
    
    for line in lines:
        try:
            line_w = draw.textlength(line, font=font)
        except Exception:
            try:
                line_w = font.getbbox(line)[2]
            except Exception:
                line_w = len(line) * (optimal_size * 0.5)
        
        x = x1_pad + (width_pad - line_w) / 2
        draw.text((x, y), line, font=font, fill=fill_color)
        y += lh + 2


def render_manga_text_layers(
    image_bytes: bytes,
    segments: list,
    project_id: str,
    font_name: str,
    font_size: int
) -> bytes:
    """
    Renders segments of translated text on top of the original image, masking out old text bubbles.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size
    
    font_bytes = None
    defaults = ["Arial", "Georgia", "Times New Roman", "Courier New", "Impact", "Noto Sans", "Noto Sans JP", "Noto Serif"]
    
    if font_name not in defaults:
        font_path = f"projects/{project_id}/fonts/{font_name}"
        try:
            font_bytes = read_binary(font_path)
        except Exception as e:
            logger.error(f"Failed to read custom font {font_name} from R2: {e}")
                
    for seg in segments:
        bbox_str = seg.get("bbox")
        target_text = seg.get("target_text") or seg.get("source_text") or ""
        if not bbox_str or not target_text.strip():
            continue
            
        try:
            bbox = json.loads(bbox_str)
        except Exception:
            continue
            
        if len(bbox) != 4:
            continue
            
        x_min, y_min, w, h = bbox
        x1 = x_min * W
        y1 = y_min * H
        x2 = (x_min + w) * W
        y2 = (y_min + h) * H
        
        # Draw white mask over original text bubble
        draw.rectangle([x1 - 2, y1 - 2, x2 + 2, y2 + 2], fill=(255, 255, 255))
        # Draw translated text inside the bubble using auto-scaling font and padding
        draw_text_wrapped(
            draw=draw,
            text=target_text,
            box=[x1, y1, x2, y2],
            font_name=font_name,
            font_bytes=font_bytes,
            initial_size=font_size,
            fill_color=(0, 0, 0)
        )
        
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    return out_buf.getvalue()
