import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("Checking imports...")
try:
    import paddleocr
    print("paddleocr imported successfully!")
except Exception as e:
    print("paddleocr import failed:", e)

try:
    import manga_ocr
    print("manga_ocr imported successfully!")
except Exception as e:
    print("manga_ocr import failed:", e)
