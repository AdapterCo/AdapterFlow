"""Synthetic layouts reproduce parser failures without inventing production data."""
import subprocess
from unittest.mock import patch

import pymupdf
import pytest

from app.importers.pdf.lehmox import LehmoxCatalogImporter
from app.services.import_service import extract_isolated
from app.storage.service import StorageService


def test_two_product_headings_merged_by_pdf_engine_are_both_preserved():
    importer = LehmoxCatalogImporter()
    lines = [
        {"bbox": (50, 100, 150, 115), "spans": [{"text": "TEST-A1"}]},
        {"bbox": (350, 100, 450, 115), "spans": [{"text": "TEST-B2"}]},
    ]
    blocks = importer._extract_text_blocks({"blocks": [{"type": 0, "bbox": (50, 100, 450, 115), "lines": lines}]}, 1)
    cards = importer._identify_product_cards(blocks, [], pymupdf.Rect(0, 0, 600, 800))
    assert {card["raw_code"] for card in cards} == {"TEST-A1", "TEST-B2"}
    assert all(importer._card_to_product(card, 1).normalized_price is None for card in cards)


def test_pdf_timeout_is_actionable_and_does_not_expose_subprocess_output(tmp_path):
    storage = StorageService(str(tmp_path))
    storage.put("test.pdf", b"%PDF-test")
    with patch("app.services.import_service.subprocess.run", side_effect=subprocess.TimeoutExpired("test", 300, stderr="private")):
        with pytest.raises(ValueError, match="5 minutos") as caught:
            extract_isolated(storage, "test.pdf")
    assert "private" not in str(caught.value)


def test_materialize_streams_source_without_loading_whole_pdf(tmp_path):
    storage = StorageService(str(tmp_path))
    storage.put("source.pdf", b"%PDF-test")
    with patch.object(storage, "get", side_effect=AssertionError("Must stream from disk")):
        with storage.materialize("source.pdf") as source:
            assert source.read_bytes() == b"%PDF-test"
        assert not source.exists()
