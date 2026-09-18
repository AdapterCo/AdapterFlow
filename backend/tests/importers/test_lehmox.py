import pytest
from decimal import Decimal
from app.importers.pdf.lehmox import normalize_price, normalize_quantity, sanitize_filename, LehmoxCatalogImporter
from app.importers.base import BaseCatalogImporter

def test_normalize_price():
    assert normalize_price("13,00") == (Decimal("13.00"), [])
    assert normalize_price("R$ 13,00") == (Decimal("13.00"), [])
    assert normalize_price("RS8.50") == (Decimal("8.50"), [])
    assert normalize_price("RS13,00") == (Decimal("13.00"), [])
    assert normalize_price("5.98") == (Decimal("5.98"), [])
    assert normalize_price("1.350,00") == (Decimal("1350.00"), [])
    assert normalize_price("  R$  25,50  ") == (Decimal("25.50"), [])
    assert normalize_price("") == (None, [])
    assert normalize_price(None) == (None, [])
    
    val, warnings = normalize_price("garbage")
    assert val is None
    assert len(warnings) == 1

def test_normalize_quantity():
    assert normalize_quantity("100") == (100, [])
    assert normalize_quantity("100 PCS") == (100, [])
    assert normalize_quantity("50pcs") == (50, [])
    assert normalize_quantity("12 pçs / cx") == (12, [])
    assert normalize_quantity("") == (None, [])
    assert normalize_quantity(None) == (None, [])
    
    val, warnings = normalize_quantity("sem quantidade")
    assert val is None
    assert len(warnings) == 1

def test_sanitize_filename():
    assert sanitize_filename("valid_name.jpg") == "valid_name.jpg"
    assert sanitize_filename("../etc/passwd") == "etc_passwd"
    assert sanitize_filename("special chars!!!.pdf") == "special_chars___.pdf"
    assert sanitize_filename("") == "unnamed"
    assert sanitize_filename(None) == "unnamed"

def test_importer_inheritance():
    importer = LehmoxCatalogImporter()
    assert isinstance(importer, BaseCatalogImporter)

def test_real_catalog_prices():
    test_cases = [
        ("Unid.CX: 4,80", Decimal("4.80")),
        ("Unid.CX: 5,68", Decimal("5.68")),
        ("Unid.CX: 5,88", Decimal("5.88")),
        ("Unid.CX: 17,00", Decimal("17.00")),
        ("Unid.CX: 11,00", Decimal("11.00")),
        ("Unid.CX: 13,00", Decimal("13.00")),
        ("Unid.CX:RS8.50", Decimal("8.50")),
        ("Unid.CX: RS5.98", Decimal("5.98")),
    ]
    for raw, expected in test_cases:
        price, warnings = normalize_price(raw)
        assert price == expected, f"Failed for {raw}: got {price}, expected {expected}"
        assert len(warnings) == 0

def test_real_catalog_quantities():
    test_cases = [
        ("PCS/CX: 400", 400),
        ("PCS/CX: 100", 100),
        ("PCS/CX:100", 100),
    ]
    for raw, expected in test_cases:
        qty, warnings = normalize_quantity(raw)
        assert qty == expected, f"Failed for {raw}: got {qty}, expected {expected}"
        assert len(warnings) == 0

def test_real_catalog_code_extraction():
    from app.importers.pdf.lehmox import PRODUCT_CODE_REGEX
    codes = [
        ("LE-520 FONTE", "LE-520"),
        ("LE-521-2", "LE-521-2"),
        ("LE-521-3", "LE-521-3"),
        ("LES-Q3B", "LES-Q3B"),
        ("LES-MOXC", "LES-MOXC"),
        ("LES-Q3E", "LES-Q3E"),
        ("LEY-2322", "LEY-2322"),
        ("LEY-12", "LEY-12"),
        ("LEY-1575", "LEY-1575"),
    ]
    for raw_text, expected_code in codes:
        match = PRODUCT_CODE_REGEX.search(raw_text)
        assert match is not None, f"Failed to match code in '{raw_text}'"
        assert match.group(1).upper() == expected_code.upper()

def test_real_catalog_dimensions_and_color():
    from app.importers.pdf.lehmox import DIMENSIONS_REGEX, COLOR_REGEX
    assert DIMENSIONS_REGEX.search('3 a 6.4" Polegadas') is not None
    assert DIMENSIONS_REGEX.search('3 a 7" Polegadas') is not None
    assert COLOR_REGEX.search('Varias Cores') is not None

def test_real_catalog_grid_extraction():
    """Test full spatial grid extraction with the 9 products from the catalog page."""
    from app.importers.pdf.lehmox import LehmoxCatalogImporter
    import fitz

    importer = LehmoxCatalogImporter()

    # Create synthetic blocks for a 595x842 page with 3 columns and 3 rows
    col_x = [60, 260, 460]
    row_y = [100, 360, 620]

    raw_products_data = [
        # Row 0
        {"code": "LE-520 FONTE", "desc": "Fonte\nEntrada USB\nV3.1A", "pcs": "PCS/CX: 400", "price": "Unid.CX: 4,80", "expected_code": "LE-520", "expected_price": Decimal("4.80"), "expected_pcs": 400},
        {"code": "LE-521-2", "desc": "Carregador V8\nEntrada USB\n3.1A", "pcs": "PCS/CX: 400", "price": "Unid.CX: 5,68", "expected_code": "LE-521-2", "expected_price": Decimal("5.68"), "expected_pcs": 400},
        {"code": "LE-521-3", "desc": "Carregador IOS\nEntrada USB\n3.1A", "pcs": "PCS/CX: 400", "price": "Unid.CX: 5,88", "expected_code": "LE-521-3", "expected_price": Decimal("5.88"), "expected_pcs": 400},
        # Row 1
        {"code": "LES-Q3B", "desc": "Mini caixa de som Bluetooth\nVarias Cores", "pcs": "PCS/CX: 100", "price": "Unid.CX: 17,00", "expected_code": "LES-Q3B", "expected_price": Decimal("17.00"), "expected_pcs": 100, "expected_color": "Varias Cores"},
        {"code": "LES-MOXC", "desc": "Mini caixa de som Bluetooth\nVarias Cores", "pcs": "PCS/CX: 100", "price": "Unid.CX: 11,00", "expected_code": "LES-MOXC", "expected_price": Decimal("11.00"), "expected_pcs": 100, "expected_color": "Varias Cores"},
        {"code": "LES-Q3E", "desc": "Mini caixa de som Bluetooth\nVarias Cores", "pcs": "PCS/CX: 100", "price": "Unid.CX: 11,00", "expected_code": "LES-Q3E", "expected_price": Decimal("11.00"), "expected_pcs": 100, "expected_color": "Varias Cores"},
        # Row 2
        {"code": "LEY-2322", "desc": "Suporte para motos Magnetico\nImã", "pcs": "PCS/CX:100", "price": "Unid.CX: 13,00", "expected_code": "LEY-2322", "expected_price": Decimal("13.00"), "expected_pcs": 100},
        {"code": "LEY-12", "desc": "Suporte Veicular\n3 a 6.4\" Polegadas", "pcs": "PCS/CX: 100", "price": "Unid.CX:RS8.50", "expected_code": "LEY-12", "expected_price": Decimal("8.50"), "expected_pcs": 100, "expected_dim": "3 a 6.4\" Polegadas"},
        {"code": "LEY-1575", "desc": "Suporte Veicular\n3 a 7\" Polegadas", "pcs": "PCS/CX: 100", "price": "Unid.CX: RS5.98", "expected_code": "LEY-1575", "expected_price": Decimal("5.98"), "expected_pcs": 100, "expected_dim": "3 a 7\" Polegadas"},
    ]

    blocks = []
    idx = 0
    for r in range(3):
        for c in range(3):
            data = raw_products_data[idx]
            bx = col_x[c]
            by = row_y[r]

            # Header code block
            blocks.append({
                "text": data["code"],
                "bbox": (bx, by, bx + 120, by + 20),
                "x0": bx, "y0": by, "x1": bx + 120, "y1": by + 20,
                "cx": bx + 60, "cy": by + 10, "page": 1,
            })
            # Description block
            blocks.append({
                "text": data["desc"],
                "bbox": (bx, by + 120, bx + 150, by + 160),
                "x0": bx, "y0": by + 120, "x1": bx + 150, "y1": by + 160,
                "cx": bx + 75, "cy": by + 140, "page": 1,
            })
            # PCS pill block
            blocks.append({
                "text": data["pcs"],
                "bbox": (bx, by + 180, bx + 70, by + 200),
                "x0": bx, "y0": by + 180, "x1": bx + 70, "y1": by + 200,
                "cx": bx + 35, "cy": by + 190, "page": 1,
            })
            # Price pill block
            blocks.append({
                "text": data["price"],
                "bbox": (bx + 80, by + 180, bx + 160, by + 200),
                "x0": bx + 80, "y0": by + 180, "x1": bx + 160, "y1": by + 200,
                "cx": bx + 120, "cy": by + 190, "page": 1,
            })
            idx += 1

    page_rect = fitz.Rect(0, 0, 595, 842)
    cards = importer._identify_product_cards(blocks, [], page_rect)

    assert len(cards) == 9, f"Expected 9 cards, got {len(cards)}"

    products = [importer._card_to_product(c, 1) for c in cards]

    for i, p in enumerate(products):
        expected = raw_products_data[i]
        assert p is not None
        assert p.normalized_code == expected["expected_code"], f"Card {i} code mismatch: {p.normalized_code} != {expected['expected_code']}"
        assert p.normalized_price == expected["expected_price"], f"Card {i} price mismatch: {p.normalized_price} != {expected['expected_price']}"
        assert p.normalized_pcs_per_box == expected["expected_pcs"], f"Card {i} pcs mismatch: {p.normalized_pcs_per_box} != {expected['expected_pcs']}"

        if "expected_dim" in expected:
            assert p.normalized_dimensions == expected["expected_dim"]
        if "expected_color" in expected:
            assert p.normalized_color == expected["expected_color"]
