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

