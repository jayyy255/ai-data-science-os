from abc import ABC, abstractmethod

class StorageProvider(ABC):

    @abstractmethod
    def upload_dataset(self, filename: str, content: bytes) -> str:
        """Uploads a dataset CSV file to the 'datasets' folder."""
        pass

    @abstractmethod
    def upload_model(self, project_id: str, model_type: str, content: bytes) -> str:
        """Uploads a trained model binary to the 'models' folder."""
        pass

    @abstractmethod
    def upload_report(self, filename: str, content: bytes) -> str:
        """Uploads a report artifact to the 'reports' folder."""
        pass

    @abstractmethod
    def upload_shap(self, filename: str, content: bytes) -> str:
        """Uploads SHAP data artifacts to the 'shap' folder."""
        pass

    @abstractmethod
    def download_file(self, path: str) -> bytes:
        """Downloads files from S3 or local fallback storage path."""
        pass

    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """Deletes files from S3 or local fallback storage path."""
        pass