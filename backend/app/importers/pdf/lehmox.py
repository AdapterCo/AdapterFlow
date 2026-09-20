"""
LehmoxCatalogImporter — Extractor for Lehmox and supplier PDF catalogs.

Uses PyMuPDF (pymupdf) to extract products from native PDF text and embedded images.
The algorithm discovers products from document structure using spatial grid analysis
and pattern matching — NO hardcoded product codes or data.

Strategy:
1. Iterate page-by-page with per-page resilience (skips blank cover pages, never halts).
2. Extract all text blocks with bounding boxes and embedded images.
3. Identify product cards via multi-strategy anchors (hyphenated codes, labeled codes, compact codes)
   with fallback to price-block clustering.
4. Extract PCS/CX quantity, unit price, dimensions, color, name, image, and out-of-stock stamps.
5. Return ExtractedProduct list with confidence scores, warnings, and raw data preserved.
"""
import re
import hashlib
import logging
from decimal import Decimal, InvalidOperation

import pymupdf as fitz
from app.core.config import settings

from app.importers.base import BaseCatalogImporter, ExtractedProduct

logger = logging.getLogger(__name__)

# Out-of-stock patterns (text and image stamps)
OUT_OF_STOCK_TEXT_REGEX = re.compile(
    r'\b(esgotad[oa]s?|sem\s+estoque|indispon[ií]vel|esgotou)\b',
    re.IGNORECASE
)

OUT_OF_STOCK_STAMP_HASHES = {
    "b7fd32bf8e33ebb50fe76b64bd23b35f",  # 464x184 red stamp
    "f0342eb538193a3d43c829572b9e7a45",  # 309x123 red stamp
    "88812db8b885bfd4eef7f2d2b47cdf24",  # 412x164 red stamp
}

# Pattern for product codes with hyphens: LE-520, LE-521-2, LES-Q3B, LES-MOXC, LEY-2322, ST-330, etc.
PRODUCT_CODE_REGEX = re.compile(
    r'\b([A-Z0-9]{1,8}\-[A-Z0-9]+(?:\-[A-Z0-9]+)?)\b',
    re.IGNORECASE
)

# Pattern for labeled codes: COD: 12345, REF: ABC, SKU: XYZ, ITEM: 99
CODE_LABELED_REGEX = re.compile(
    r'\b(?:C[ÓO]D(?:IGO)?\.?|REF(?:ER[EÊ]NCIA)?\.?|ITEM|SKU|MODELO)\s*[:#\-]?\s*([A-Z0-9\-_]{2,25})\b',
    re.IGNORECASE
)

# Pattern for compact alphanumeric codes: ST330, LE520, SM10, IP12, G10, V8
CODE_ALPHANUM_REGEX = re.compile(
    r'\b([A-Z]{1,5}\d{2,6}[A-Z0-9\-]*)\b',
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
    if "-" in original:
        return None, ["Preço negativo ou ambíguo: requer revisão."]

    pill_match = PRICE_PILL_REGEX.search(original)
    if pill_match:
        target_str = pill_match.group(1)
    else:
        clean = re.sub(r'(?i)\s*(?:Unid\.?\s*CX\s*:?|R\s*\$|RS)\s*', '', original).strip()
        gen_match = PRICE_GENERIC_REGEX.search(clean)
        target_str = gen_match.group(1) if gen_match else clean

    if not target_str:
        return None, []

    try:
        has_dot = '.' in target_str
        has_comma = ',' in target_str

        if has_dot and has_comma:
            clean = target_str.replace('.', '').replace(',', '.')
        elif has_comma:
            clean = target_str.replace(',', '.')
        else:
            clean = target_str

        value = Decimal(clean)

        if not value.is_finite():
            return None, ["Preço não finito: requer revisão."]
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
    pill_match = PCS_REGEX.search(raw)
    if pill_match:
        return int(pill_match.group(1)), warnings

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
    Importer for Lehmox and multi-supplier PDF catalogs.
    
    Discovers products from document structure using spatial analysis.
    Does NOT hardcode any specific product codes or data.
    """

    def extract(self, file_path: str, storage_service=None) -> list[ExtractedProduct]:
        """Extract products from a supplier PDF catalog with page-by-page resilience."""
        logger.info(f"Starting PDF extraction: {file_path}")

        doc = fitz.open(file_path)
        all_products: list[ExtractedProduct] = []

        try:
            if not doc.is_pdf or doc.needs_pass:
                raise ValueError("PDF inválido ou protegido por senha.")
            total_pages = len(doc)
            if total_pages == 0:
                raise ValueError("O documento PDF não contém páginas.")

            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_num = page_idx + 1

                try:
                    logger.debug(f"Processing page {page_num}/{total_pages}")

                    # 1. Extract text blocks with position info
                    text_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
                    raw_text = page.get_text().strip()

                    # Handle page without native selectable text (e.g. cover page, graphic banner)
                    if not raw_text:
                        if settings.OCR_ENABLED:
                            try:
                                textpage = page.get_textpage_ocr(language=settings.OCR_LANGUAGE, dpi=150, full=True)
                                text_data = page.get_text("dict", textpage=textpage)
                            except Exception as ocr_err:
                                logger.warning(f"OCR failed on page {page_num}: {ocr_err}")
                                continue
                        else:
                            logger.info(f"Page {page_num} has no selectable text (cover or graphic). Continuing to next page.")
                            continue

                    text_blocks = self._extract_text_blocks(text_data, page_num)
                    if not text_blocks:
                        continue

                    # 2. Extract embedded images
                    image_info = self._extract_images(doc, page, page_num)

                    # 3. Identify product cards via spatial analysis
                    product_cards = self._identify_product_cards(text_blocks, image_info, page.rect, page_num)

                    # 4. Convert to ExtractedProduct
                    for card in product_cards:
                        product = self._card_to_product(card, page_num)
                        if product:
                            all_products.append(product)

                except Exception as page_err:
                    logger.warning(f"Page {page_num} could not be fully parsed ({type(page_err).__name__}: {page_err}). Continuing.")
                    continue

        finally:
            doc.close()

        logger.info(f"PDF extraction complete: {len(all_products)} products found across {total_pages} pages")
        return all_products

    def _extract_text_blocks(self, text_data: dict, page_num: int) -> list[dict]:
        """Extract text blocks with their bounding boxes and content."""
        blocks = []
        source_blocks = []
        for block in text_data.get("blocks", []):
            lines = block.get("lines", [])
            codes = {match.group(1).upper() for line in lines for span in line.get("spans", [])
                     for match in PRODUCT_CODE_REGEX.finditer(span.get("text", ""))}
            if block.get("type") == 0 and len(codes) > 1:
                source_blocks.extend({"type": 0, "lines": [line], "bbox": line["bbox"]} for line in lines)
            else:
                source_blocks.append(block)

        for block in source_blocks:
            if block.get("type") != 0:
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
                for rect in img_rects:
                    images.append({
                        "xref": xref, "data": base_image["image"],
                        "ext": base_image.get("ext", "png"),
                        "width": base_image.get("width", 0), "height": base_image.get("height", 0),
                        "bbox": (rect.x0, rect.y0, rect.x1, rect.y1),
                        "cx": (rect.x0 + rect.x1) / 2, "cy": (rect.y0 + rect.y1) / 2,
                        "page": page_num,
                    })
            except Exception as e:
                logger.warning(f"Failed to extract image xref={xref} on page {page_num}: {e}")

        return images

    def _identify_product_cards(
        self,
        text_blocks: list[dict],
        images: list[dict],
        page_rect: fitz.Rect,
        page_num: int = 1,
    ) -> list[dict]:
        """
        Identify product cards using spatial grid analysis with multi-strategy fallback.
        """
        page_h = page_rect.height if page_rect else 842
        page_w = page_rect.width if page_rect else 595

        usable_blocks = [
            b for b in text_blocks
            if b["cy"] > 0.03 * page_h and b["cy"] < 0.98 * page_h
        ]

        # Find code banner anchors
        code_anchors = []
        for block in usable_blocks:
            match = PRODUCT_CODE_REGEX.search(block["text"])
            code_found = match.group(1).upper() if match else None

            if not code_found:
                match_labeled = CODE_LABELED_REGEX.search(block["text"])
                if match_labeled:
                    code_found = match_labeled.group(1).upper()

            if not code_found and len(block["text"].splitlines()) <= 2 and len(block["text"]) <= 20:
                match_alphanum = CODE_ALPHANUM_REGEX.search(block["text"])
                if match_alphanum:
                    code_found = match_alphanum.group(1).upper()

            if code_found:
                code_anchors.append({
                    "block": block,
                    "code": code_found,
                    "cx": block["cx"],
                    "cy": block["cy"],
                    "x0": block["x0"],
                    "y0": block["y0"],
                    "x1": block["x1"],
                    "y1": block["y1"],
                })

        # FALLBACK STRATEGY: If no code anchors found on page, find products by Price Blocks
        if not code_anchors:
            price_blocks = [
                b for b in usable_blocks
                if PRICE_PILL_REGEX.search(b["text"]) or PRICE_GENERIC_REGEX.search(b["text"])
            ]
            for idx, pb in enumerate(price_blocks):
                above_blocks = [b for b in usable_blocks if b["cy"] < pb["cy"] and abs(b["cx"] - pb["cx"]) < 120]
                above_blocks.sort(key=lambda b: pb["cy"] - b["cy"])
                title_block = above_blocks[0] if above_blocks else pb
                first_word = title_block["text"].split()[0] if title_block["text"] else f"P{page_num}-{idx+1}"
                fallback_code = re.sub(r'[^A-Z0-9\-]', '', first_word.upper())[:15] or f"P{page_num}-{idx+1}"

                code_anchors.append({
                    "block": title_block,
                    "code": fallback_code,
                    "cx": pb["cx"],
                    "cy": pb["cy"],
                    "x0": pb["x0"],
                    "y0": title_block["y0"],
                    "x1": pb["x1"],
                    "y1": pb["y1"],
                })

        if not code_anchors:
            return []

        code_anchors.sort(key=lambda a: (round(a["cy"] / 80) * 80, a["cx"]))

        cards: list[dict] = []

        for i, anchor in enumerate(code_anchors):
            left_neighbors = [a for a in code_anchors if a["cx"] < anchor["cx"] - 30 and abs(a["cy"] - anchor["cy"]) < 100]
            right_neighbors = [a for a in code_anchors if a["cx"] > anchor["cx"] + 30 and abs(a["cy"] - anchor["cy"]) < 100]

            cell_x0 = (max(a["cx"] for a in left_neighbors) + anchor["cx"]) / 2 if left_neighbors else max(0, anchor["x0"] - 30)
            cell_x1 = (right_neighbors[0]["cx"] + anchor["cx"]) / 2 if right_neighbors else min(page_w, anchor["x1"] + 150)

            cell_y0 = anchor["y0"] - 15

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
                "is_out_of_stock": False,
            }

            for block in usable_blocks:
                if cell_x0 <= block["cx"] <= cell_x1 and cell_y0 <= block["cy"] <= cell_y1:
                    card["text_blocks"].append(block)

            for img in images:
                if cell_x0 <= img["cx"] <= cell_x1 and cell_y0 <= img["cy"] <= cell_y1:
                    if self._is_out_of_stock_stamp(img):
                        card["is_out_of_stock"] = True
                        continue
                    card["images"].append(img)

            self._parse_card_fields(card, anchor)
            cards.append(card)

        return cards

    def _is_out_of_stock_stamp(self, img: dict) -> bool:
        """Check if an image matches known or heuristic ESGOTADO stamp parameters."""
        data = img.get("data")
        if not data:
            return False
        h = hashlib.md5(data).hexdigest()
        if h in OUT_OF_STOCK_STAMP_HASHES:
            return True
        return False

    def _parse_card_fields(self, card: dict, anchor: dict) -> None:
        """Parse the collected blocks in a card into structured fields."""
        description_lines: list[str] = []

        header_text = anchor["block"]["text"].strip()
        code = anchor["code"]
        remainder_header = re.sub(re.escape(code), '', header_text, flags=re.IGNORECASE).strip()

        for block in card["text_blocks"]:
            text = block["text"].strip()
            lines = [l.strip() for l in text.split('\n') if l.strip()]

            for line in lines:
                if OUT_OF_STOCK_TEXT_REGEX.search(line):
                    card["is_out_of_stock"] = True
                    continue

                pcs_match = PCS_REGEX.search(line)
                if pcs_match:
                    card["raw_pcs_per_box"] = line
                    continue

                price_match = PRICE_PILL_REGEX.search(line)
                if price_match:
                    card["raw_price"] = line
                    continue

                dim_match = DIMENSIONS_REGEX.search(line)
                if dim_match:
                    card["raw_dimensions"] = dim_match.group(1).strip()
                    continue

                color_match = COLOR_REGEX.search(line)
                if color_match and ("cor" in line.lower() or "cores" in line.lower() or "sortid" in line.lower()):
                    card["raw_color"] = color_match.group(1).strip()
                    continue

                if PRODUCT_CODE_REGEX.search(line) and len(line) <= len(code) + 15:
                    continue

                if line.lower() not in ["novidades", "lehmox", "voltar ao topo"]:
                    description_lines.append(line)

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

        raw_name = card.get("raw_name")
        normalized_name = raw_name.strip() if raw_name else None
        if not normalized_name:
            warnings.append("Product name not detected")
            confidence -= 0.2

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

        raw_pcs = card.get("raw_pcs_per_box")
        normalized_pcs = None
        if raw_pcs:
            normalized_pcs, pcs_warnings = normalize_quantity(raw_pcs)
            warnings.extend(pcs_warnings)

        raw_dimensions = card.get("raw_dimensions")
        raw_color = card.get("raw_color")

        image_data = None
        image_ext = None
        if card.get("images"):
            card["images"].sort(key=lambda img: img.get("width", 0) * img.get("height", 0), reverse=True)
            primary_img = card["images"][0]
            image_data = primary_img.get("data")
            image_ext = primary_img.get("ext", "png")
        else:
            confidence -= 0.1

        is_out_of_stock = card.get("is_out_of_stock", False)
        if is_out_of_stock:
            warnings.append("Item marcado como ESGOTADO no catálogo do fornecedor")

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
            is_out_of_stock=is_out_of_stock,
        )
