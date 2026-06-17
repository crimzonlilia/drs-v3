import io
from PIL import Image, ImageDraw
from server.utils.graphics import parse_text_into_units, draw_text_wrapped

def test_ruby_rendering():
    # 1. Test unit parsing
    test_text = "Con mồi[cái cổ] của ta, là Viện trưởng[Olga Marie] của ta"
    units = parse_text_into_units(test_text)
    
    print("Parsed units:")
    for u in units:
        print(f"  Text: {repr(u.text)}, Ruby: {repr(u.ruby)}")
        
    assert units[1].text == "mồi"
    assert units[1].ruby == "cái cổ"
    assert units[5].text == "Viện"
    assert units[6].text == "trưởng"
    assert units[6].ruby == "Olga Marie"

    # 2. Test rendering on mock canvas
    img = Image.new("RGB", (400, 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw a bounding box for the text
    box = [50, 50, 350, 150]
    draw.rectangle(box, outline=(200, 200, 200), width=1)
    
    draw_text_wrapped(
        draw=draw,
        text=test_text,
        box=box,
        font_name="arial",
        font_bytes=None,
        initial_size=20,
        fill_color=(0, 0, 0)
    )
    
    # Save the output image
    img.save("scratch/test_ruby_output.png")
    print("Successfully rendered and saved scratch/test_ruby_output.png")

if __name__ == "__main__":
    test_ruby_rendering()
