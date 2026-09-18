from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from decimal import Decimal

@dataclass
class ExtractedProduct:
    raw_code: Optional[str]
    raw_name: Optional[str]
    raw_price: Optional[str]
    raw_dimensions: Optional[str]
    raw_pcs_per_box: Optional[str]
    raw_color: Optional[str]
    normalized_code: Optional[str]
    normalized_name: Optional[str]
    normalized_price: Optional[Decimal]
    normalized_dimensions: Optional[str]
    normalized_pcs_per_box: Optional[int]
    normalized_color: Optional[str]
    image_data: Optional[bytes]
    image_extension: Optional[str]
    confidence: float
    warnings: List[str]
    page_number: Optional[int] = None
    bbox: Optional[tuple] = None

class BaseCatalogImporter(ABC):
    @abstractmethod
    def extract(self, file_path: str, storage_service) -> List[ExtractedProduct]:
        pass
