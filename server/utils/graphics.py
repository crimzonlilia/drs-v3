import io
import json
import logging
from PIL import Image, ImageDraw, ImageFont
from core.utils.r2 import read_binary

logger = logging.getLogger(__name__)

def draw_text_wrapped(draw: ImageDraw.ImageDraw, text: str, box: list, font: ImageFont.ImageFont, fill_color=(0, 0, 0)):
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    
    # Simple word wrapping
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
            
        if line_w > width and len(current_line) > 1:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    # Draw vertical centering
    try:
        line_heights = []
        for l in lines:
            try:
                bbox = font.getbbox(l)
                line_heights.append(bbox[3] - bbox[1])
            except Exception:
                line_heights.append(16)
        total_text_height = sum(line_heights) + (len(lines) - 1) * 2
    except Exception:
        total_text_height = len(lines) * 16
        
    y = y1 + (height - total_text_height) / 2
    
    for line in lines:
        try:
            line_w = draw.textlength(line, font=font)
        except Exception:
            try:
                line_w = font.getbbox(line)[2]
            except Exception:
                line_w = len(line) * 8
        x = x1 + (width - line_w) / 2
        draw.text((x, y), line, font=font, fill=fill_color)
        
        try:
            bbox = font.getbbox(line)
            y += (bbox[3] - bbox[1]) + 2
        except Exception:
            y += 18


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
    img = Image.open(io.BytesIO(image_bytes))
    draw = ImageDraw.Draw(img)
    W, H = img.size
    
    font = None
    defaults = ["Arial", "Georgia", "Times New Roman", "Courier New", "Impact", "Noto Sans", "Noto Sans JP", "Noto Serif"]
    
    if font_name not in defaults:
        font_path = f"projects/{project_id}/fonts/{font_name}"
        font_bytes = read_binary(font_path)
        if font_bytes:
            try:
                font = ImageFont.truetype(io.BytesIO(font_bytes), font_size)
            except Exception as e:
                logger.error(f"Failed to load custom font {font_name} from R2: {e}")
                
    if font is None:
        try:
            font = ImageFont.truetype(font_name.lower() + ".ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
                
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
        # Draw translated text inside the bubble
        draw_text_wrapped(draw, target_text, [x1, y1, x2, y2], font, fill_color=(0, 0, 0))
        
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    return out_buf.getvalue()
