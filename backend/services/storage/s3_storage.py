import os
import boto3
from services.storage.base import StorageProvider

class S3Storage(StorageProvider):
    def __init__(self):
        # Configure AWS credentials from environment
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET", "aidso-prod")
        
        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def upload_dataset(self, filename: str, content: bytes) -> str:
        key = f"datasets/{filename}"
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content
        )
        return f"s3://{self.bucket_name}/{key}"

    def upload_model(self, project_id: str, model_type: str, content: bytes) -> str:
        key = f"models/{project_id}/{model_type}.pkl"
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content
        )
        return f"s3://{self.bucket_name}/{key}"

    def upload_report(self, filename: str, content: bytes) -> str:
        key = f"reports/{filename}"
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content
        )
        return f"s3://{self.bucket_name}/{key}"

    def upload_shap(self, filename: str, content: bytes) -> str:
        key = f"shap/{filename}"
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content
        )
        return f"s3://{self.bucket_name}/{key}"

    def download_file(self, path: str) -> bytes:
        if path.startswith("s3://"):
            bucket_and_key = path[5:]
            bucket, key = bucket_and_key.split("/", 1)
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        raise ValueError(f"S3Storage download_file expects an s3:// URL, received: {path}")

    def delete_file(self, path: str) -> bool:
        if path.startswith("s3://"):
            try:
                bucket_and_key = path[5:]
                bucket, key = bucket_and_key.split("/", 1)
                self.client.delete_object(Bucket=bucket, Key=key)
                return True
            except Exception as e:
                print(f"S3 delete failed: {e}")
                return False
        return False