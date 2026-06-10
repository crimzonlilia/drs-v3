from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class OCRBlock:
    text: str
    bbox: list[float]  # [x_min, y_min, width, height] normalized to 0.0 - 1.0
    confidence: float

class OCRProvider(ABC):
    @abstractmethod
    async def extract(self, image_path: str) -> list[OCRBlock]:
        """
        Extract text blocks with normalized coordinates from the image at image_path.
        """
        pass
