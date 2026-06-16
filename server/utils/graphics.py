import io
import json
import logging
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

def get_text_height(lines: list, font: ImageFont.ImageFont) -> int:
    line_heights = []
    for l in lines:
        try:
            bbox = font.getbbox(l)
            line_heights.append(bbox[3] - bbox[1])
        except Exception:
            line_heights.append(16)
    if not line_heights:
        return 0
    return sum(line_heights) + (len(lines) - 1) * 2

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
    
    # 1. Find optimal font size starting from user preference or bubble max
    max_size = max(initial_size, 28)
    font, optimal_size = find_optimal_font_size(draw, text, width_pad, height_pad, font_name, font_bytes, max_size)
    
    # 2. Wrap text into lines using the optimal font size
    lines = wrap_text_to_lines(draw, text, width_pad, font)
    
    # 3. Calculate vertically centered Y coordinate
    total_text_height = get_text_height(lines, font)
    y = y1_pad + (height_pad - total_text_height) / 2
    
    # 4. Draw each line with horizontal centering
    for line in lines:
        try:
            line_w = draw.textlength(line, font=font)
        except Exception:
            try:
                line_w = font.getbbox(line)[2]
            except Exception:
                line_w = len(line) * (optimal_size * 0.5)
        
        # Center the text horizontally within the padded width
        x = x1_pad + (width_pad - line_w) / 2
        draw.text((x, y), line, font=font, fill=fill_color)
        
        try:
            bbox = font.getbbox(line)
            y += (bbox[3] - bbox[1]) + 2
        except Exception:
            y += (optimal_size + 2)


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
