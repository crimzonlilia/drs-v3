import io
import json
import logging
import re
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from core.utils.r2 import read_binary

logger = logging.getLogger(__name__)

Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class MangaTextLayout:
    box: Box
    lines: list[str]
    font: ImageFont.ImageFont
    font_size: int
    line_height: int
    line_spacing: int
    total_height: int


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def clamp_box(box: Box, image_size: tuple[int, int]) -> Box:
    width, height = image_size
    x1, y1, x2, y2 = box
    x1 = clamp(x1, 0, width)
    y1 = clamp(y1, 0, height)
    x2 = clamp(x2, 0, width)
    y2 = clamp(y2, 0, height)
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return x1, y1, x2, y2


def parse_ocr_bbox(bbox: list[float], image_size: tuple[int, int]) -> Box | None:
    if len(bbox) != 4:
        return None

    width, height = image_size
    x_min, y_min, w, h = [float(v) for v in bbox]

    if max(abs(x_min), abs(y_min), abs(w), abs(h)) <= 1.5:
        x1 = x_min * width
        y1 = y_min * height
        x2 = (x_min + w) * width
        y2 = (y_min + h) * height
    else:
        x1 = x_min
        y1 = y_min
        x2 = x_min + w
        y2 = y_min + h

    return clamp_box((x1, y1, x2, y2), image_size)


def pixel_luminance(pixel: tuple[int, ...]) -> float:
    r, g, b = pixel[:3]
    return (0.299 * r) + (0.587 * g) + (0.114 * b)


def is_bubble_fill_pixel(pixel: tuple[int, ...]) -> bool:
    r, g, b = pixel[:3]
    return pixel_luminance(pixel) >= 205 and (max(r, g, b) - min(r, g, b)) <= 42


def detect_bubble_fill_region(img: Image.Image, ocr_box: Box) -> Box | None:
    """
    Find the connected light fill surrounding the OCR text. This preserves the
    current stage boundary: a future detector can still replace Stage 2, while
    this heuristic gives today's renderer the full bubble instead of the text box.
    """
    width, height = img.size
    pixels = img.load()
    x1, y1, x2, y2 = [int(round(v)) for v in ocr_box]
    ocr_w = max(1, x2 - x1)
    ocr_h = max(1, y2 - y1)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    offsets = [
        (0, 0),
        (0, -ocr_h),
        (0, ocr_h),
        (-ocr_w, 0),
        (ocr_w, 0),
        (-ocr_w // 2, -ocr_h // 2),
        (ocr_w // 2, -ocr_h // 2),
        (-ocr_w // 2, ocr_h // 2),
        (ocr_w // 2, ocr_h // 2),
    ]
    seeds = []
    for dx, dy in offsets:
        sx = int(clamp(cx + dx, 0, width - 1))
        sy = int(clamp(cy + dy, 0, height - 1))
        if is_bubble_fill_pixel(pixels[sx, sy]):
            seeds.append((sx, sy))

    if not seeds:
        return None

    step = max(1, min(width, height) // 900)
    max_component = int((width * height) / (step * step) * 0.35)
    best_box: Box | None = None
    best_area = 0

    for seed in seeds:
        queue = [seed]
        visited = {seed}
        min_x = max_x = seed[0]
        min_y = max_y = seed[1]
        area = 0
        touches_edge = False

        while queue:
            x, y = queue.pop()
            area += 1
            if area > max_component:
                touches_edge = True
                break

            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            if x <= step or y <= step or x >= width - step - 1 or y >= height - step - 1:
                touches_edge = True

            for nx, ny in ((x + step, y), (x - step, y), (x, y + step), (x, y - step)):
                if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in visited:
                    continue
                if is_bubble_fill_pixel(pixels[nx, ny]):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        region_w = max_x - min_x
        region_h = max_y - min_y
        if touches_edge or region_w < ocr_w * 1.35 or region_h < ocr_h * 1.8:
            continue

        if area > best_area:
            pad = max(4, int(min(region_w, region_h) * 0.025))
            best_box = clamp_box((min_x - pad, min_y - pad, max_x + pad, max_y + pad), img.size)
            best_area = area

    return best_box


def compute_render_region(
    ocr_box: Box,
    image_size: tuple[int, int],
    bubble_box: Box | None = None,
    image: Image.Image | None = None,
) -> Box:
    """
    Stage 2: estimate the full dialogue region from OCR text bounds.
    A future speech-bubble detector can pass bubble_box and bypass this heuristic.
    """
    if bubble_box:
        return clamp_box(bubble_box, image_size)

    if image:
        detected_region = detect_bubble_fill_region(image, ocr_box)
        if detected_region:
            return detected_region

    x1, y1, x2, y2 = ocr_box
    box_w = max(1.0, x2 - x1)
    box_h = max(1.0, y2 - y1)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    small_box_boost = 1.7 if min(box_w, box_h) < 80 else 1.2
    target_w = max(box_w * 2.8 * small_box_boost, box_h * 7.5, 130.0)
    target_h = max(box_h * 5.0 * small_box_boost, box_w * 1.15, 90.0)
    target_w = min(target_w, image_size[0] * 0.82)
    target_h = min(target_h, image_size[1] * 0.55)

    region = (cx - target_w / 2, cy - target_h / 2, cx + target_w / 2, cy + target_h / 2)
    return clamp_box(region, image_size)


def compute_text_layout_region(render_region: Box) -> Box:
    x1, y1, x2, y2 = render_region
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    margin_x = clamp(width * 0.12, 8, 26)
    margin_y = clamp(height * 0.14, 8, 28)
    return (x1 + margin_x, y1 + margin_y, x2 - margin_x, y2 - margin_y)


def sample_text_cleanup_color(img: Image.Image, ocr_box: Box) -> tuple[int, int, int]:
    """
    Estimate the bubble fill color near the OCR text. Prefer bright pixels so
    original black glyphs do not pull the cleanup fill toward gray.
    """
    x1, y1, x2, y2 = [int(round(v)) for v in ocr_box]
    width, height = img.size
    pad = max(2, int(max(x2 - x1, y2 - y1) * 0.08))
    sample_box = clamp_box((x1 - pad, y1 - pad, x2 + pad, y2 + pad), img.size)
    sx1, sy1, sx2, sy2 = [int(round(v)) for v in sample_box]

    pixels = []
    for y in range(sy1, max(sy1, sy2)):
        for x in range(sx1, max(sx1, sx2)):
            on_border = x < x1 or x >= x2 or y < y1 or y >= y2
            if not on_border or x < 0 or x >= width or y < 0 or y >= height:
                continue
            r, g, b = img.getpixel((x, y))[:3]
            if (r + g + b) / 3 >= 185:
                pixels.append((r, g, b))

    if not pixels:
        return (255, 255, 255)

    pixels.sort(key=lambda p: p[0] + p[1] + p[2])
    mid = pixels[len(pixels) // 2]
    return int(mid[0]), int(mid[1]), int(mid[2])


def remove_original_text(img: Image.Image, ocr_box: Box) -> None:
    """
    Stage 3: remove only the OCR text area. This avoids the old full-bubble
    ellipse wipe and leaves the outline/artwork outside the text untouched.
    """
    draw = ImageDraw.Draw(img)
    x1, y1, x2, y2 = ocr_box
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    pad_x = clamp(width * 0.07, 2, 8)
    pad_y = clamp(height * 0.07, 2, 8)
    cleanup_box = clamp_box((x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y), img.size)
    fill = sample_text_cleanup_color(img, ocr_box)
    draw.rounded_rectangle(cleanup_box, radius=max(2, int(min(width, height) * 0.08)), fill=fill)

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


def measure_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, fallback_size: int = 16) -> float:
    try:
        return draw.textlength(text, font=font)
    except Exception:
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0]
        except Exception:
            return len(text) * (fallback_size * 0.55)


def split_long_token(draw: ImageDraw.ImageDraw, token: str, width: float, font: ImageFont.ImageFont, fallback_size: int) -> list[str]:
    parts = []
    current = ""
    for char in token:
        trial = current + char
        if current and measure_text_width(draw, trial, font, fallback_size) > width:
            parts.append(current)
            current = char
        else:
            current = trial
    if current:
        parts.append(current)
    return parts or [token]


def wrap_text_balanced(draw: ImageDraw.ImageDraw, text: str, width: float, font: ImageFont.ImageFont, font_size: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = ""
    for word in words:
        candidates = [word]
        if measure_text_width(draw, word, font, font_size) > width:
            candidates = split_long_token(draw, word, width, font, font_size)

        for token in candidates:
            trial = f"{current} {token}".strip()
            if not current or measure_text_width(draw, trial, font, font_size) <= width:
                current = trial
            else:
                lines.append(current)
                current = token

    if current:
        lines.append(current)
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
            
    normalized = font_name.strip().lower()
    font_candidates = {
        "arial": ["arial.ttf", "C:\\Windows\\Fonts\\arial.ttf"],
        "georgia": ["georgia.ttf", "C:\\Windows\\Fonts\\georgia.ttf"],
        "times new roman": ["times.ttf", "times new roman.ttf", "C:\\Windows\\Fonts\\times.ttf"],
        "courier new": ["cour.ttf", "courier new.ttf", "C:\\Windows\\Fonts\\cour.ttf"],
        "impact": ["impact.ttf", "C:\\Windows\\Fonts\\impact.ttf"],
        "noto sans": ["NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"],
        "noto sans jp": ["NotoSansJP-Regular.otf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"],
        "noto serif": ["NotoSerif-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf"],
    }
    candidates = font_candidates.get(normalized, [])
    candidates.extend([
        font_name,
        normalized + ".ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ])

    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue

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
    min_size = 9

    def fits_size(size: int) -> bool:
        font = load_font_at_size(font_name, font_bytes, size)
        lines = wrap_text_balanced(draw, text, width, font, size)
        total_height = get_text_height(lines, font)
        fits = True
        if total_height > height:
            fits = False
        else:
            for l in lines:
                if measure_text_width(draw, l, font, size) > width:
                    fits = False
                    break
        return fits

    best_size = min_size
    low, high = min_size, max_size
    while low <= high:
        mid = (low + high) // 2
        if fits_size(mid):
            best_size = mid
            low = mid + 1
        else:
            high = mid - 1

    return load_font_at_size(font_name, font_bytes, best_size), best_size


def get_layout_height(lines: list[str], font: ImageFont.ImageFont, font_size: int) -> tuple[int, int, int]:
    line_height = max(get_font_line_height(font), int(font_size * 1.08))
    line_spacing = max(3, int(font_size * 0.14))
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * line_spacing
    return line_height, line_spacing, total_height


def layout_score(draw: ImageDraw.ImageDraw, lines: list[str], width: float, height: float, font: ImageFont.ImageFont, font_size: int) -> float:
    if not lines:
        return float("inf")

    line_height, _, total_height = get_layout_height(lines, font, font_size)
    line_widths = [measure_text_width(draw, line, font, font_size) for line in lines]
    widest = max(line_widths) if line_widths else 0
    avg_width = sum(line_widths) / len(line_widths) if line_widths else 0
    raggedness = sum(abs(w - avg_width) for w in line_widths) / max(1, len(line_widths))
    vertical_fill = total_height / max(1, height)
    horizontal_fill = widest / max(1, width)
    target_fill_penalty = abs(vertical_fill - 0.50) * 55 + abs(horizontal_fill - 0.84) * 35
    lonely_last_line = 0
    if len(line_widths) > 1 and line_widths[-1] < avg_width * 0.45:
        lonely_last_line = 18

    return target_fill_penalty + (raggedness / max(1, width)) * 35 + lonely_last_line + len(lines) * 0.4 + line_height * 0.02


def layout_fits(draw: ImageDraw.ImageDraw, layout: MangaTextLayout, width: float, height: float) -> bool:
    if layout.total_height > height:
        return False
    return all(measure_text_width(draw, line, layout.font, layout.font_size) <= width for line in layout.lines)


def compute_layout_for_font_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    layout_box: Box,
    font_name: str,
    font_bytes: bytes,
    font_size: int,
) -> MangaTextLayout | None:
    x1, y1, x2, y2 = layout_box
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    font = load_font_at_size(font_name, font_bytes, font_size)
    best: MangaTextLayout | None = None
    best_score = float("inf")

    for width_ratio in (1.0, 0.94, 0.88, 0.82):
        candidate_width = width * width_ratio
        lines = wrap_text_balanced(draw, text, candidate_width, font, font_size)
        line_height, line_spacing, total_height = get_layout_height(lines, font, font_size)
        candidate_box = (
            x1 + (width - candidate_width) / 2,
            y1,
            x2 - (width - candidate_width) / 2,
            y2,
        )
        layout = MangaTextLayout(candidate_box, lines, font, font_size, line_height, line_spacing, total_height)
        if not layout_fits(draw, layout, candidate_width, height):
            continue

        score = layout_score(draw, lines, candidate_width, height, font, font_size)
        if score < best_score:
            best = layout
            best_score = score

    return best


def compute_optimal_text_layout(
    draw: ImageDraw.ImageDraw,
    text: str,
    layout_box: Box,
    font_name: str,
    font_bytes: bytes,
    requested_size: int,
) -> MangaTextLayout | None:
    x1, y1, x2, y2 = layout_box
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    min_size = 9
    max_size = int(max(requested_size, min(54, max(28, height * 0.34, width * 0.14))))

    best: MangaTextLayout | None = None
    low, high = min_size, max_size
    while low <= high:
        mid = (low + high) // 2
        layout = compute_layout_for_font_size(draw, text, layout_box, font_name, font_bytes, mid)
        if layout:
            best = layout
            low = mid + 1
        else:
            high = mid - 1

    if best:
        return best

    return compute_layout_for_font_size(draw, text, layout_box, font_name, font_bytes, min_size)


def draw_manga_layout(draw: ImageDraw.ImageDraw, layout: MangaTextLayout, fill_color=(0, 0, 0)) -> None:
    x1, y1, x2, y2 = layout.box
    width = max(1.0, x2 - x1)
    y = y1 + (max(1.0, y2 - y1) - layout.total_height) / 2
    for line in layout.lines:
        line_w = measure_text_width(draw, line, layout.font, layout.font_size)
        x = x1 + (width - line_w) / 2
        draw.text((x, y), line, font=layout.font, fill=fill_color)
        y += layout.line_height + layout.line_spacing

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
    min_size = 9

    def fits_size(size: int) -> bool:
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
        return fits

    best_size = min_size
    low, high = min_size, max_size
    while low <= high:
        mid = (low + high) // 2
        if fits_size(mid):
            best_size = mid
            low = mid + 1
        else:
            high = mid - 1

    font = load_font_at_size(font_name, font_bytes, best_size)
    ruby_font = load_font_at_size(font_name, font_bytes, max(8, int(best_size * 0.45)))
    return font, ruby_font, best_size

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
    
    # Apply padding to prevent text clipping at speech bubble edges (reduce to 6% for more text space)
    pad_x = max(2, int(width * 0.06))
    pad_y = max(2, int(height * 0.06))
    
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
        
    # Fallback to standard manga paragraph layout if no ruby markup is present.
    layout = compute_optimal_text_layout(
        draw=draw,
        text=text,
        layout_box=(x1_pad, y1_pad, x2_pad, y2_pad),
        font_name=font_name,
        font_bytes=font_bytes,
        requested_size=initial_size,
    )
    if layout:
        draw_manga_layout(draw, layout, fill_color=fill_color)


def draw_debug_regions(draw: ImageDraw.ImageDraw, ocr_box: Box, render_region: Box, layout_region: Box) -> None:
    draw.rectangle(ocr_box, outline=(255, 0, 0), width=2)
    draw.rectangle(render_region, outline=(0, 180, 0), width=2)
    draw.rectangle(layout_region, outline=(0, 90, 255), width=2)


def render_manga_text_layers(
    image_bytes: bytes,
    segments: list,
    project_id: str,
    font_name: str,
    font_size: int,
    debug: bool = False
) -> bytes:
    """
    Renders translated manga text through separate OCR, region, cleanup,
    layout, font optimization, and drawing stages.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    image_size = img.size
    
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
            
        ocr_box = parse_ocr_bbox(bbox, image_size)
        if not ocr_box:
            continue

        render_region = compute_render_region(ocr_box, image_size, image=img)
        layout_region = compute_text_layout_region(render_region)

        remove_original_text(img, ocr_box)

        if '[' in target_text:
            draw_text_wrapped(
                draw=draw,
                text=target_text,
                box=list(layout_region),
                font_name=font_name,
                font_bytes=font_bytes,
                initial_size=font_size,
                fill_color=(0, 0, 0)
            )
        else:
            layout = compute_optimal_text_layout(
                draw=draw,
                text=target_text,
                layout_box=layout_region,
                font_name=font_name,
                font_bytes=font_bytes,
                requested_size=font_size,
            )
            if layout:
                draw_manga_layout(draw, layout, fill_color=(0, 0, 0))
                layout_region = layout.box

        if debug:
            draw_debug_regions(draw, ocr_box, render_region, layout_region)
        
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    return out_buf.getvalue()
