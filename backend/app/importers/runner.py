"""Isolated, bounded PDF extraction subprocess. No database or tokens required."""
import base64
import json
import sys
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from app.importers.pdf.lehmox import LehmoxCatalogImporter
import pymupdf as fitz


def encode(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    output = Path(sys.argv[2])
    try:
        importer = LehmoxCatalogImporter()
        if len(sys.argv) > 3 and sys.argv[3] == "--metadata":
            result = importer.metadata(sys.argv[1])
        elif len(sys.argv) > 4 and sys.argv[3] == "--page":
            with fitz.open(sys.argv[1]) as document:
                result = importer.extract_page(document, int(sys.argv[4]))
        else:
            result = importer.extract(sys.argv[1])
        output.write_text(json.dumps(result, default=encode), encoding="utf-8")
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else "PDF inválido ou OCR indisponível."
        output.write_text(json.dumps({"error": message}), encoding="utf-8")
        sys.exit(1)
