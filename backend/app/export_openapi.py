"""Export contracts without connecting to a database or remote service."""
import json
from pathlib import Path
from app.main import app

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
    destination.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
