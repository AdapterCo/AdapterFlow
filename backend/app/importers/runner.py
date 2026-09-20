"""Isolated, bounded PDF extraction subprocess. No database or tokens required."""
import base64
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from app.importers.pdf.lehmox import LehmoxCatalogImporter


def encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    output = Path(sys.argv[2])
    try:
        items = LehmoxCatalogImporter().extract(sys.argv[1])
        output.write_text(json.dumps([asdict(item) for item in items], default=encode), encoding="utf-8")
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else "PDF inválido ou OCR indisponível."
        output.write_text(json.dumps({"error": message}), encoding="utf-8")
        sys.exit(1)
