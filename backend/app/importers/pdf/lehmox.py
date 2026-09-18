"""
LehmoxCatalogImporter — Extractor for Lehmox supplier PDF catalogs.

Uses PyMuPDF (pymupdf/fitz) to extract products from native PDF text and embedded images.
The algorithm discovers products from document structure using spatial grid analysis
and pattern matching — NO hardcoded product codes or data.

Strategy:
1. Extract all text blocks with bounding boxes
2. Extract all embedded images with positions
3. Identify product code patterns via regex (e.g. LE-520, LES-Q3B, LEY-2322)
4. Group text blocks and images into spatial grid cells (columns x rows)
5. For each cell:
   - Extract code (from top banner, e.g. "LE-520 FONTE" -> code="LE-520")
   - Extract PCS/CX quantity (e.g. "PCS/CX: 400" -> 400)
   - Extract Unid.CX unit price (e.g. "Unid.CX: 13,00" -> 13.00, "Unid.CX:RS8.50" -> 8.50)
   - Extract dimensions/compatibility (e.g. '3 a 6.4" Polegadas')
   - Extract explicit color if stated (e.g. "Varias Cores")
   - Assemble product name from description lines
   - Associate embedded image by cell containment
6. Return ExtractedProduct list with confidence scores, warnings, and raw data preserved
"""
import re
import logging
from typing import Optional
from decimal import Decimal, InvalidOperation

import fitz  # PyMuPDF

from app.importers.base import BaseCatalogImporter, ExtractedProduct

logger = logging.getLogger(__name__)

# Pattern for product codes in banner: LE-520, LE-521-2, LES-Q3B, LES-MOXC, LEY-2322, LEY-12, etc.
PRODUCT_CODE_REGEX = re.compile(
    r'\b([A-Z]{2,6}\-[A-Z0-9]+(?:\-[A-Z0-9]+)?)\b',
    re.IGNORECASE
)

# Pill patterns for PCS/CX and Unid.CX
PCS_REGEX = re.compile(
    r'(?:PCS|PÇS|PEÇAS|UNID)\s*/\s*CX\s*:\s*(\d+)',
    re.IGNORECASE
)
FALLBACK_PCS_REGEX = re.compile(
    r'\b(\d+)\s*(?:pcs|pçs|peças|unid|und)\b',
    re.IGNORECASE
)

# Price patterns: Unid.CX: 4,80 | Unid.CX:RS8.50 | Unid.CX: RS5.98 | R$ 13,00
PRICE_PILL_REGEX = re.compile(
    r'Unid\.?\s*CX\s*:\s*(?:RS|R\$)?\s*(\d{1,3}(?:[.,]\d{1,3})*(?:[.,]\d{2}))',
    re.IGNORECASE
)
PRICE_GENERIC_REGEX = re.compile(
    r'(?:R\$|RS|R\s*\$)?\s*(\d{1,3}(?:[.,]\d{1,3})*(?:[.,]\d{2}))',
    re.IGNORECASE
)

# Dimensions/compatibility patterns: 3 a 6.4" Polegadas, 3 a 7" Polegadas
DIMENSIONS_REGEX = re.compile(
    r'(\d+(?:\.\d+)?\s*(?:a|à|-)\s*\d+(?:\.\d+)?["\']?\s*(?:polegadas|pol\.?)?)',
    re.IGNORECASE
)

# Explicit color text in catalog: Varias Cores, Sortido, Preto, etc.
COLOR_REGEX = re.compile(
    r'\b(V[aá]rias\s+Cores|Sortid[oa]s?|Preto|Branco|Azul|Vermelho|Verde|Rosa|Roxo|Amarelo|Cinza|Dourado|Prata)\b',
    re.IGNORECASE
)


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
    - "Unid.CX:RS8.50" -> 8.50
    - "" -> None
    - garbage -> None with warning
    """
    if not raw or not raw.strip():
        return None, []

    warnings: list[str] = []
    original = raw.strip()

    # Extract numeric price part if inside label e.g. "Unid.CX:RS8.50"
    pill_match = PRICE_PILL_REGEX.search(original)
    if pill_match:
        target_str = pill_match.group(1)
    else:
        # Strip prefixes
        clean = re.sub(r'(?i)\s*(?:Unid\.?\s*CX\s*:?|R\s*\$|RS)\s*', '', original).strip()
        gen_match = PRICE_GENERIC_REGEX.search(clean)
        target_str = gen_match.group(1) if gen_match else clean

    if not target_str:
        return None, []

    try:
        has_dot = '.' in target_str
        has_comma = ',' in target_str

        if has_dot and has_comma:
            # e.g. "1.350,00" -> thousands dot, decimal comma
            clean = target_str.replace('.', '').replace(',', '.')
        elif has_comma:
            # e.g. "13,00" -> decimal comma
            clean = target_str.replace(',', '.')
        else:
            # e.g. "8.50" -> decimal dot
            clean = target_str

        value = Decimal(clean)

        if value < 0:
            warnings.append(f"Negative price detected: {original}")

        return value, warnings

    except (InvalidOperation, ValueError, ArithmeticError):
        warnings.append(f"Failed to normalize price: {original}")
        return None, warnings


def normalize_quantity(raw: str) -> tuple[int | None, list[str]]:
    """Extract integer quantity from raw text (e.g. PCS/CX: 400 -> 400)."""
    if not raw or not raw.strip():
        return None, []

    warnings: list[str] = []
    # Try PCS pill regex first
    pill_match = PCS_REGEX.search(raw)
    if pill_match:
        return int(pill_match.group(1)), warnings

    # Fallback to general number extraction
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
    """Sanitize filename to prevent path traversal and invalid characters."""
    if not name:
        return "unnamed"

    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    clean = clean.replace('..', '')
    clean = clean.strip('_')
    return clean or "unnamed"


class LehmoxCatalogImporter(BaseCatalogImporter):
    """
    Importer for Lehmox supplier PDF catalogs.
    
    Discovers products from document structure using spatial grid analysis.
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

                # 3. Identify product cards via spatial analysis
                product_cards = self._identify_product_cards(text_blocks, image_info, page.rect)

                # 4. Convert to ExtractedProduct
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

            text = "\n".join(block_text_parts).strip()
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
                "cx": (bbox[0] + bbox[2]) / 2,
                "cy": (bbox[1] + bbox[3]) / 2,
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

                img_rects = page.get_image_rects(xref)
                bbox = None
                cx, cy = 0.0, 0.0
                if img_rects:
                    rect = img_rects[0]
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                    cx = (rect.x0 + rect.x1) / 2
                    cy = (rect.y0 + rect.y1) / 2

                images.append({
                    "xref": xref,
                    "data": base_image["image"],
                    "ext": base_image.get("ext", "png"),
                    "width": base_image.get("width", 0),
                    "height": base_image.get("height", 0),
                    "bbox": bbox,
                    "cx": cx,
                    "cy": cy,
                    "page": page_num,
                })
            except Exception as e:
                logger.warning(f"Failed to extract image xref={xref} on page {page_num}: {e}")

        return images

    def _identify_product_cards(
        self,
        text_blocks: list[dict],
        images: list[dict],
        page_rect: fitz.Rect
    ) -> list[dict]:
        """
        Identify product cards using spatial grid analysis.
        
        1. Find all product code banners (anchors)
        2. Cluster anchors into rows and columns
        3. Form rectangular cell boundaries for each card
        4. Assign text blocks and images to each cell
        5. Parse card attributes
        """
        # Filter out header ("NOVIDADES", "LEHMOX") and footer ("Voltar ao topo", page number)
        page_h = page_rect.height if page_rect else 842
        page_w = page_rect.width if page_rect else 595

        usable_blocks = [
            b for b in text_blocks
            if b["cy"] > 0.04 * page_h and b["cy"] < 0.98 * page_h
        ]

        # Find code banner anchors
        code_anchors = []
        for block in usable_blocks:
            match = PRODUCT_CODE_REGEX.search(block["text"])
            if match:
                code_anchors.append({
                    "block": block,
                    "code": match.group(1).upper(),
                    "cx": block["cx"],
                    "cy": block["cy"],
                    "x0": block["x0"],
                    "y0": block["y0"],
                    "x1": block["x1"],
                    "y1": block["y1"],
                })

        if not code_anchors:
            logger.warning("No product code anchors found on page")
            return []

        # Sort anchors top-to-bottom, left-to-right
        code_anchors.sort(key=lambda a: (round(a["cy"] / 80) * 80, a["cx"]))

        # Determine column count and column boundaries
        # Group x coordinates of anchors (e.g. 3 columns)
        x_coords = sorted(set(round(a["cx"] / 30) * 30 for a in code_anchors))
        y_coords = sorted(set(round(a["cy"] / 50) * 50 for a in code_anchors))

        cards: list[dict] = []

        # For each anchor, determine its card bounding box
        for i, anchor in enumerate(code_anchors):
            # Find horizontal bounds
            # Left: halfway between this anchor and the nearest anchor to the left (or 0)
            # Right: halfway between this anchor and the nearest anchor to the right (or page_w)
            left_neighbors = [a for a in code_anchors if a["cx"] < anchor["cx"] - 30 and abs(a["cy"] - anchor["cy"]) < 100]
            right_neighbors = [a for a in code_anchors if a["cx"] > anchor["cx"] + 30 and abs(a["cy"] - anchor["cy"]) < 100]

            cell_x0 = (left_neighbors[0]["cx"] + anchor["cx"]) / 2 if left_neighbors else max(0, anchor["x0"] - 30)
            cell_x1 = (right_neighbors[0]["cx"] + anchor["cx"]) / 2 if right_neighbors else min(page_w, anchor["x1"] + 150)

            # Find vertical bounds
            # Top: just above the anchor
            cell_y0 = anchor["y0"] - 15

            # Bottom: before the next row anchor in the same column (or page bottom)
            below_neighbors = [a for a in code_anchors if a["cy"] > anchor["cy"] + 50 and abs(a["cx"] - anchor["cx"]) < 60]
            if below_neighbors:
                cell_y1 = below_neighbors[0]["y0"] - 10
            else:
                cell_y1 = page_h - 10

            card = {
                "raw_code": anchor["code"],
                "header_block": anchor["block"],
                "cell_bbox": (cell_x0, cell_y0, cell_x1, cell_y1),
                "text_blocks": [],
                "images": [],
                "raw_name": None,
                "raw_price": None,
                "raw_pcs_per_box": None,
                "raw_dimensions": None,
                "raw_color": None,
            }

            # Assign text blocks within this cell
            for block in usable_blocks:
                if cell_x0 <= block["cx"] <= cell_x1 and cell_y0 <= block["cy"] <= cell_y1:
                    card["text_blocks"].append(block)

            # Assign images within this cell
            for img in images:
                if cell_x0 <= img["cx"] <= cell_x1 and cell_y0 <= img["cy"] <= cell_y1:
                    card["images"].append(img)

            # Parse fields within this card
            self._parse_card_fields(card, anchor)
            cards.append(card)

        return cards

    def _parse_card_fields(self, card: dict, anchor: dict) -> None:
        """Parse the collected blocks in a card into structured fields."""
        description_lines: list[str] = []

        # Check if code header has extra text (e.g. "LE-520 FONTE" -> "FONTE")
        header_text = anchor["block"]["text"].strip()
        code = anchor["code"]
        remainder_header = re.sub(re.escape(code), '', header_text, flags=re.IGNORECASE).strip()

        for block in card["text_blocks"]:
            text = block["text"].strip()
            lines = [l.strip() for l in text.split('\n') if l.strip()]

            for line in lines:
                # 1. Check PCS/CX pill
                pcs_match = PCS_REGEX.search(line)
                if pcs_match:
                    card["raw_pcs_per_box"] = line
                    continue

                # 2. Check Unid.CX price pill
                price_match = PRICE_PILL_REGEX.search(line)
                if price_match:
                    card["raw_price"] = line
                    continue

                # 3. Check Dimensions
                dim_match = DIMENSIONS_REGEX.search(line)
                if dim_match:
                    card["raw_dimensions"] = dim_match.group(1).strip()
                    continue

                # 4. Check Color
                color_match = COLOR_REGEX.search(line)
                if color_match and ("cor" in line.lower() or "cores" in line.lower() or "sortid" in line.lower()):
                    card["raw_color"] = color_match.group(1).strip()
                    continue

                # 5. Check if it's the code itself
                if PRODUCT_CODE_REGEX.search(line) and len(line) <= len(code) + 15:
                    continue

                # 6. Otherwise it's a description/name line
                # Ignore header/footer artefacts
                if line.lower() not in ["novidades", "lehmox", "voltar ao topo"]:
                    description_lines.append(line)

        # Assemble product name
        name_parts = []
        if remainder_header and not any(remainder_header.lower() in d.lower() for d in description_lines):
            name_parts.append(remainder_header.title())

        name_parts.extend(description_lines)
        if name_parts:
            card["raw_name"] = " ".join(name_parts).strip()

    def _card_to_product(self, card: dict, page_num: int) -> ExtractedProduct | None:
        """Convert parsed card dictionary to ExtractedProduct dataclass."""
        raw_code = card.get("raw_code")
        if not raw_code:
            return None

        warnings: list[str] = []
        confidence = 1.0

        normalized_code = raw_code.strip().upper()

        # Name
        raw_name = card.get("raw_name")
        normalized_name = raw_name.strip() if raw_name else None
        if not normalized_name:
            warnings.append("Product name not detected")
            confidence -= 0.2

        # Price
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
            warnings.append("Price not detected")

        # Quantity (PCS/CX)
        raw_pcs = card.get("raw_pcs_per_box")
        normalized_pcs = None
        if raw_pcs:
            normalized_pcs, pcs_warnings = normalize_quantity(raw_pcs)
            warnings.extend(pcs_warnings)

        # Dimensions & Color
        raw_dimensions = card.get("raw_dimensions")
        raw_color = card.get("raw_color")

        # Primary Image (pick the largest image in the cell if multiple)
        image_data = None
        image_ext = None
        if card.get("images"):
            # Sort by area (width * height) descending
            card["images"].sort(key=lambda img: img.get("width", 0) * img.get("height", 0), reverse=True)
            primary_img = card["images"][0]
            image_data = primary_img.get("data")
            image_ext = primary_img.get("ext", "png")
        else:
            confidence -= 0.1

        confidence = max(0.0, min(1.0, confidence))

        if confidence < 0.6:
            warnings.append("Low confidence — manual review recommended")

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
            normalized_dimensions=raw_dimensions,
            normalized_pcs_per_box=normalized_pcs,
            normalized_color=raw_color,
            image_data=image_data,
            image_extension=image_ext,
            confidence=confidence,
            warnings=warnings,
            page_number=page_num,
            bbox=card.get("cell_bbox"),
        )
