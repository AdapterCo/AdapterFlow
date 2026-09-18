import os
from pathlib import Path

class StorageService:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _get_full_path(self, path: str) -> Path:
        # Sanitize to prevent path traversal
        clean_path = str(path).lstrip('/').replace('..', '')
        full_path = (self.base_path / clean_path).resolve()
        if not str(full_path).startswith(str(self.base_path)):
            raise ValueError("Invalid path")
        return full_path
        
    def put(self, path: str, data: bytes) -> str:
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return str(path)
        
    def get(self, path: str) -> bytes:
        full_path = self._get_full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_bytes()
        
    def delete(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False
        
    def exists(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        return full_path.exists()
        
    def get_url(self, path: str) -> str:
        # For local dev, this might just be an API endpoint that serves the file
        return f"/api/v1/storage/{path}"
