"""
LehmoxCatalogImporter — Extractor for Lehmox supplier PDF catalogs.

Uses PyMuPDF (fitz) to extract products from native PDF text and embedded images.
The algorithm discovers products from document structure using spatial analysis
and pattern matching — NO hardcoded product codes or data.

Strategy:
1. Extract all text blocks with bounding boxes
2. Extract all embedded images with positions
3. Identify product code patterns via regex
4. Group nearby text blocks into product card regions
5. For each card: extract code, name, price, PCS/CX, dimensions, color
6. Associate images to products by spatial proximity
7. Normalize extracted values
8. Return results with confidence scores and warnings
"""
import re
import logging
from typing import Optional
from decimal import Decimal, InvalidOperation

import fitz  # PyMuPDF

from app.importers.base import BaseCatalogImporter, ExtractedProduct

logger = logging.getLogger(__name__)

# Pattern for product codes like LEY-2322, ABC-123, XY-1, CODE1234
PRODUCT_CODE_PATTERN = re.compile(r'^[A-Z]{2,10}[\-]?\d{1,6}[A-Z]?$', re.IGNORECASE)

# Price patterns
PRICE_PATTERN = re.compile(
    r'(?:R\$|RS|R\s*\$)?\s*(\d{1,3}(?:[.,]\d{1,3})*(?:[.,]\d{2}))',
    re.IGNORECASE
)

# PCS/CX pattern
PCS_PATTERN = re.compile(r'(\d+)\s*(?:pcs|pçs|peças|un|unid|und)?(?:\s*/?\s*(?:cx|caixa|box|pct|pacote))?', re.IGNORECASE)


def normalize_price(raw: str) -> tuple[Decimal | None, list[str]]:
    """
    Normalize price string to Decimal.
    
    Handles formats:
    - "13,00" -> 13.00
    - "R$ 13,00" -> 13.00
    - "RS8.50" -> 8.50
    - "RS13,00" -> 13.00
    - "5.98" -> 5.98
    - "1.350,00" -> 1350.00
    - "" -> None
    - garbage -> None with warning
    """
    if not raw or not raw.strip():
        return None, []

    warnings: list[str] = []
    original = raw

    # Remove currency symbols and whitespace
    clean = re.sub(r'(?i)\s*R\s*\$\s*|\s*RS\s*', '', raw).strip()

    if not clean:
        return None, []

    try:
        # Detect format: if both dot and comma exist
        has_dot = '.' in clean
        has_comma = ',' in clean

        if has_dot and has_comma:
            # Format like "1.350,00" (thousands dot, decimal comma)
            clean = clean.replace('.', '').replace(',', '.')
        elif has_comma:
            # Format like "13,00" (decimal comma)
            clean = clean.replace(',', '.')
        # else: format like "8.50" (decimal dot) — leave as is

        value = Decimal(clean)

        if value < 0:
            warnings.append(f"Negative price detected: {original}")

        return value, warnings

    except (InvalidOperation, ValueError, ArithmeticError):
        warnings.append(f"Failed to normalize price: {original}")
        return None, warnings


def normalize_quantity(raw: str) -> tuple[int | None, list[str]]:
    """Extract integer quantity from raw text."""
    if not raw or not raw.strip():
        return None, []

    warnings: list[str] = []
    match = re.search(r'\d+', raw)
    if match:
        try:
            value = int(match.group())
            if value > 0:
                return value, warnings
            else:
                warnings.append(f"Non-positive quantity: {raw}")
                return None, warnings
        except ValueError:
            warnings.append(f"Failed to parse quantity: {raw}")
            return None, warnings

    warnings.append(f"No numeric value found in quantity: {raw}")
    return None, warnings


def sanitize_filename(name: str) -> str:
    """
    Sanitize filename to prevent path traversal and invalid characters.
    """
    if not name:
        return "unnamed"

    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    clean = clean.replace('..', '')
    clean = clean.strip('_')
    return clean or "unnamed"


class LehmoxCatalogImporter(BaseCatalogImporter):
    """
    Importer for Lehmox supplier PDF catalogs.
    
    Discovers products from document structure using spatial analysis.
    Does NOT hardcode any specific product codes or data.
    """

    def extract(self, file_path: str, storage_service=None) -> list[ExtractedProduct]:
        """Extract products from a Lehmox PDF catalog."""
        logger.info(f"Starting Lehmox PDF extraction: {file_path}")

        doc = fitz.open(file_path)
        all_products: list[ExtractedProduct] = []

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1

                logger.debug(f"Processing page {page_num}")

                # 1. Extract text blocks with position info
                text_data = page.get_text("dict")
                text_blocks = self._extract_text_blocks(text_data, page_num)

                # 2. Extract embedded images
                image_info = self._extract_images(doc, page, page_num)

                # 3. Identify product cards
                product_cards = self._identify_product_cards(text_blocks)

                # 4. Associate images with product cards
                self._associate_images(product_cards, image_info)

                # 5. Convert to ExtractedProduct
                for card in product_cards:
                    product = self._card_to_product(card, page_num)
                    if product:
                        all_products.append(product)

        finally:
            doc.close()

        logger.info(f"Lehmox extraction complete: {len(all_products)} products found")
        return all_products

    def _extract_text_blocks(self, text_data: dict, page_num: int) -> list[dict]:
        """Extract text blocks with their bounding boxes and content."""
        blocks = []
        for block in text_data.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue

            block_text_parts = []
            for line in block.get("lines", []):
                line_text = " ".join(
                    span.get("text", "").strip()
                    for span in line.get("spans", [])
                    if span.get("text", "").strip()
                )
                if line_text:
                    block_text_parts.append(line_text)

            text = " ".join(block_text_parts).strip()
            if not text:
                continue

            bbox = block.get("bbox", (0, 0, 0, 0))
            blocks.append({
                "text": text,
                "bbox": tuple(bbox),
                "x0": bbox[0],
                "y0": bbox[1],
                "x1": bbox[2],
                "y1": bbox[3],
                "page": page_num,
            })

        return blocks

    def _extract_images(self, doc: fitz.Document, page: fitz.Page, page_num: int) -> list[dict]:
        """Extract embedded images from a page with their positions."""
        images = []
        seen_xrefs = set()

        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base_image = doc.extract_image(xref)
                if not base_image or not base_image.get("image"):
                    continue

                # Get image position on page
                img_rects = page.get_image_rects(xref)
                bbox = None
                if img_rects:
                    rect = img_rects[0]
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1)

                images.append({
                    "xref": xref,
                    "data": base_image["image"],
                    "ext": base_image.get("ext", "png"),
                    "width": base_image.get("width", 0),
                    "height": base_image.get("height", 0),
                    "bbox": bbox,
                    "page": page_num,
                })
            except Exception as e:
                logger.warning(f"Failed to extract image xref={xref} on page {page_num}: {e}")

        return images

    def _identify_product_cards(self, text_blocks: list[dict]) -> list[dict]:
        """
        Identify product cards by finding product code patterns
        and grouping nearby text blocks.
        """
        cards: list[dict] = []

        # Find blocks that contain product codes
        code_blocks = []
        for block in text_blocks:
            text = block["text"].strip()
            # Check if this looks like a product code
            if PRODUCT_CODE_PATTERN.match(text):
                code_blocks.append(block)

        if not code_blocks:
            logger.warning("No product codes found on page")
            return cards

        # For each code, create a card and associate nearby text blocks
        for i, code_block in enumerate(code_blocks):
            card = {
                "code_block": code_block,
                "raw_code": code_block["text"].strip(),
                "text_blocks": [],
                "image": None,
                "raw_name": None,
                "raw_price": None,
                "raw_pcs_per_box": None,
                "raw_dimensions": None,
                "raw_color": None,
            }

            # Define region: from this code to the next code (or page bottom)
            y_start = code_block["y0"] - 20  # small margin above
            if i + 1 < len(code_blocks):
                y_end = code_blocks[i + 1]["y0"] - 5
            else:
                y_end = code_block["y1"] + 300  # generous region below

            x_start = code_block["x0"] - 100
            x_end = code_block["x1"] + 300

            # Collect blocks in this region
            for block in text_blocks:
                if block is code_block:
                    continue
                if (block["y0"] >= y_start and block["y1"] <= y_end and
                        block["x0"] >= max(0, x_start)):
                    card["text_blocks"].append(block)

            # Parse the card text blocks
            self._parse_card_fields(card)

            cards.append(card)

        return cards

    def _parse_card_fields(self, card: dict) -> None:
        """Parse text blocks within a card to identify fields."""
        for block in card["text_blocks"]:
            text = block["text"].strip()
            text_upper = text.upper()

            # Try to identify field type

            # Price detection
            if card["raw_price"] is None:
                price_match = PRICE_PATTERN.search(text)
                if price_match or any(
                    indicator in text_upper
                    for indicator in ['R$', 'RS', 'PREÇO', 'PRECO', 'VALOR']
                ):
                    card["raw_price"] = text

            # PCS/CX detection
            if card["raw_pcs_per_box"] is None:
                if any(indicator in text_upper for indicator in ['PCS', 'PÇS', 'PEÇAS', '/CX', 'CAIXA', 'UNID']):
                    card["raw_pcs_per_box"] = text
                elif re.match(r'^\d+\s*(pcs|un|und|pçs)', text, re.IGNORECASE):
                    card["raw_pcs_per_box"] = text

            # Dimensions detection
            if card["raw_dimensions"] is None:
                if re.search(r'\d+\s*[xX×]\s*\d+', text) or any(
                    indicator in text_upper for indicator in ['CM', 'MM', 'DIMENSÃO', 'DIMENSAO', 'TAMANHO']
                ):
                    card["raw_dimensions"] = text

            # Color detection
            if card["raw_color"] is None:
                color_keywords = [
                    'PRETO', 'BRANCO', 'AZUL', 'VERMELHO', 'VERDE', 'AMARELO',
                    'ROSA', 'ROXO', 'LARANJA', 'CINZA', 'MARROM', 'DOURADO',
                    'PRATA', 'TRANSPARENTE', 'COLORIDO', 'SORTIDO',
                    'BLACK', 'WHITE', 'BLUE', 'RED', 'GREEN', 'YELLOW', 'PINK'
                ]
                if any(color in text_upper for color in color_keywords):
                    card["raw_color"] = text

            # Name detection (fallback: first unclassified text that's long enough)
            if (card["raw_name"] is None and
                    card["raw_price"] != text and
                    card["raw_pcs_per_box"] != text and
                    card["raw_dimensions"] != text and
                    card["raw_color"] != text and
                    len(text) > 3 and
                    not PRODUCT_CODE_PATTERN.match(text)):
                card["raw_name"] = text

    def _associate_images(self, cards: list[dict], images: list[dict]) -> None:
        """Associate extracted images with product cards by spatial proximity."""
        if not images or not cards:
            return

        for card in cards:
            code_block = card["code_block"]
            code_center_y = (code_block["y0"] + code_block["y1"]) / 2
            code_center_x = (code_block["x0"] + code_block["x1"]) / 2

            best_image = None
            best_distance = float('inf')

            for img in images:
                if img.get("bbox") is None:
                    continue

                img_bbox = img["bbox"]
                img_center_y = (img_bbox[1] + img_bbox[3]) / 2
                img_center_x = (img_bbox[0] + img_bbox[2]) / 2

                # Calculate distance
                dist = ((code_center_x - img_center_x) ** 2 +
                        (code_center_y - img_center_y) ** 2) ** 0.5

                # Image should be reasonably close
                if dist < best_distance and dist < 500:
                    best_distance = dist
                    best_image = img

            if best_image:
                card["image"] = best_image

    def _card_to_product(self, card: dict, page_num: int) -> ExtractedProduct | None:
        """Convert a parsed card into an ExtractedProduct."""
        raw_code = card.get("raw_code")
        if not raw_code:
            return None

        warnings: list[str] = []
        confidence = 1.0

        # Normalize code
        normalized_code = raw_code.strip().upper()

        # Normalize name
        raw_name = card.get("raw_name")
        normalized_name = raw_name.strip() if raw_name else None
        if not normalized_name:
            warnings.append("Product name not detected")
            confidence -= 0.2

        # Normalize price
        raw_price = card.get("raw_price")
        normalized_price = None
        if raw_price:
            normalized_price, price_warnings = normalize_price(raw_price)
            warnings.extend(price_warnings)
            if normalized_price is None:
                confidence -= 0.2
                warnings.append("Price extraction requires review")
        else:
            confidence -= 0.1

        # Normalize PCS/CX
        raw_pcs = card.get("raw_pcs_per_box")
        normalized_pcs = None
        if raw_pcs:
            normalized_pcs, pcs_warnings = normalize_quantity(raw_pcs)
            warnings.extend(pcs_warnings)

        # Dimensions and color
        raw_dimensions = card.get("raw_dimensions")
        raw_color = card.get("raw_color")

        # Image data
        image_data = None
        image_ext = None
        if card.get("image"):
            image_data = card["image"]["data"]
            image_ext = card["image"].get("ext", "png")
        else:
            confidence -= 0.1

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))

        # Mark for review if confidence is low
        if confidence < 0.6:
            warnings.append("Low confidence — manual review recommended")

        code_bbox = card["code_block"]["bbox"] if card.get("code_block") else None

        return ExtractedProduct(
            raw_code=raw_code,
            raw_name=raw_name,
            raw_price=raw_price,
            raw_dimensions=raw_dimensions,
            raw_pcs_per_box=raw_pcs,
            raw_color=raw_color,
            normalized_code=normalized_code,
            normalized_name=normalized_name,
            normalized_price=normalized_price,
            normalized_dimensions=raw_dimensions,  # preserve as-is for now
            normalized_pcs_per_box=normalized_pcs,
            normalized_color=raw_color,  # preserve as-is for now
            image_data=image_data,
            image_extension=image_ext,
            confidence=confidence,
            warnings=warnings,
            page_number=page_num,
            bbox=code_bbox,
        )
