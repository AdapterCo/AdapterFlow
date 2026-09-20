import os
import pytest
from app.importers.pdf.lehmox import LehmoxCatalogImporter

def test_out_of_stock_stamp_detection_unit():
    importer = LehmoxCatalogImporter()
    
    # Aspect ratio alone must never imply stock availability
    fake_stamp_img = {
        "data": b"non-matching-data",
        "width": 464,
        "height": 184, # ratio = 464 / 184 = 2.5217
        "ext": "png"
    }
    assert importer._is_out_of_stock_stamp(fake_stamp_img) is False

    # Check normal product image (e.g. 800x800 or 500x300)
    normal_img = {
        "data": b"product-data",
        "width": 600,
        "height": 600,
        "ext": "jpg"
    }
    assert importer._is_out_of_stock_stamp(normal_img) is False

def test_out_of_stock_with_real_pdf_if_available():
    pdf_path = r"C:\Users\AdapterCO\Desktop\TrabalhoFelipe\LEHMOX  2026.09.16 (02).pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Real PDF not found in local path, skipping integration assertion.")

    import fitz
    doc = fitz.open(pdf_path)
    # Page 107 (0-indexed: 106)
    page_107 = doc[106]
    
    importer = LehmoxCatalogImporter()
    text_data = page_107.get_text("dict")
    text_blocks = importer._extract_text_blocks(text_data, 107)
    image_info = importer._extract_images(doc, page_107, 107)
    cards = importer._identify_product_cards(text_blocks, image_info, page_107.rect)
    
    # Should identify cards including ST-681 or ST-682 as out of stock
    out_of_stock_codes = [c["raw_code"] for c in cards if c.get("is_out_of_stock")]
    assert len(out_of_stock_codes) >= 1
    
    # Products converted
    products = [importer._card_to_product(c, 107) for c in cards]
    out_of_stock_prods = [p for p in products if p and p.is_out_of_stock]
    assert len(out_of_stock_prods) >= 1
    assert any("ESGOTADO" in w for p in out_of_stock_prods for w in p.warnings)
    doc.close()
