import os
from services.storage.base import StorageProvider
from services.storage.minio_storage import MinIOStorage
from services.storage.s3_storage import S3Storage

_storage_instance = None

def get_storage_provider() -> StorageProvider:
    global _storage_instance
    if _storage_instance is None:
        env = os.getenv("ENVIRONMENT", "local")
        if env == "local":
            _storage_instance = MinIOStorage()
        else:
            _storage_instance = S3Storage()
    return _storage_instance
