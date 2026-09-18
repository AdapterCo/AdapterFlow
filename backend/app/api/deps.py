from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.storage.service import StorageService
from app.core.config import settings

def get_storage() -> StorageService:
    return StorageService(settings.STORAGE_PATH)

DBSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[StorageService, Depends(get_storage)]
