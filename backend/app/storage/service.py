from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from tempfile import NamedTemporaryFile
from urllib.parse import quote
import shutil


class StorageService:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        if not path or Path(path).is_absolute() or PureWindowsPath(path).drive or chr(92) in path:
            raise ValueError("Caminho de armazenamento inválido.")
        if any(part in ("..", ".") for part in path.split("/")):
            raise ValueError("Caminho de armazenamento inválido.")
        full_path = (self.base_path / path).resolve()
        if not full_path.is_relative_to(self.base_path) or full_path == self.base_path:
            raise ValueError("Caminho de armazenamento inválido.")
        return full_path

    def put(self, path: str, data: bytes) -> str:
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open("xb") as file:
            file.write(data)
        return path

    def get(self, path: str) -> bytes:
        return self._get_full_path(path).read_bytes()

    def delete(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        if not full_path.is_file():
            return False
        full_path.unlink()
        return True

    def exists(self, path: str) -> bool:
        return self._get_full_path(path).is_file()

    def get_url(self, path: str) -> str:
        self._get_full_path(path)
        return f"/api/v1/storage/{quote(path, safe='/')}"

    @contextmanager
    def materialize(self, path: str):
        temporary_path = None
        try:
            with NamedTemporaryFile(suffix=Path(path).suffix, delete=False) as file:
                temporary_path = Path(file.name)
                with self._get_full_path(path).open("rb") as source:
                    shutil.copyfileobj(source, file, length=1024 * 1024)
            yield temporary_path
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
