import os
import uuid
import shutil
import logging
from abc import ABC, abstractmethod
from fastapi import UploadFile
from app.config import settings

logger = logging.getLogger("uvicorn")

class StorageProvider(ABC):
    @abstractmethod
    async def upload_file(self, file: UploadFile, category: str) -> str:
        """Uploads a file and returns its access URL or path."""
        pass

class LocalStorageProvider(StorageProvider):
    async def upload_file(self, file: UploadFile, category: str) -> str:
        
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        
        
        target_dir = os.path.join(settings.UPLOAD_DIR, category)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, unique_filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return path that can be served by FastAPI static files mount
        # e.g., /uploads/photos/uuid.jpg
        return f"/uploads/{category}/{unique_filename}"

# Factory function to get the configured storage provider
def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider()

