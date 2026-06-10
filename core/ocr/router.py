from __future__ import annotations

from core.ocr.base import OCRProvider
from core.ocr.manga_ocr import MangaOCRProvider
from core.ocr.paddle_ocr import PaddleOCRProvider

class OCRRouter:
    @staticmethod
    def get_provider(source_lang: str) -> OCRProvider:
        """
        Route to MangaOCR for Japanese and PaddleOCR for other languages.
        """
        if source_lang.lower() == "ja":
            return MangaOCRProvider()
        return PaddleOCRProvider()
