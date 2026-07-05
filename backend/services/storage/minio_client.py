import os
import boto3
from botocore.client import Config

class MinIOClient:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "password123")
        
        self.bucket_name = "aidso-runs"
        self.local_fallback_dir = "./tmp/minio_fallback"
        
        try:
            self.s3 = boto3.client(
                's3',
                endpoint_url=f"http://{endpoint}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            # Try to check connection/create bucket
            self.s3.create_bucket(Bucket=self.bucket_name)
            self.client_enabled = True
        except Exception as e:
            print(f"MinIO client initialization failed (falling back to local directories): {e}")
            self.client_enabled = False
            os.makedirs(self.local_fallback_dir, exist_ok=True)

    def upload_dataset(self, filename: str, content: bytes):
        """
        Uploads raw dataset csv to s3 datasets bucket.
        """
        if self.client_enabled:
            try:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=f"datasets/{filename}",
                    Body=content
                )
                return f"s3://{self.bucket_name}/datasets/{filename}"
            except Exception as e:
                print(f"Failed uploading to MinIO: {e}")
        
        # Local fallback
        filepath = os.path.join(self.local_fallback_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return f"file://{os.path.abspath(filepath)}"

    def upload_model(self, model_name: str, version: str, content: bytes):
        """
        Stores trained XGBoost/LightGBM binary binaries in MinIO buckets.
        """
        key = f"models/{model_name}/{version}.bin"
        if self.client_enabled:
            try:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content
                )
                return f"s3://{self.bucket_name}/{key}"
            except Exception as e:
                print(f"Failed uploading model to MinIO: {e}")
        
        # Local fallback
        filepath = os.path.join(self.local_fallback_dir, f"{model_name}_{version}.bin")
        with open(filepath, 'wb') as f:
            f.write(content)
        return f"file://{os.path.abspath(filepath)}"

    def download_file(self, path: str) -> bytes:
        """
        Downloads file content from S3 or local directory.
        """
        if path.startswith("s3://"):
            try:
                bucket_and_key = path[5:]
                bucket, key = bucket_and_key.split("/", 1)
                response = self.s3.get_object(Bucket=bucket, Key=key)
                return response['Body'].read()
            except Exception as e:
                print(f"S3 download failed: {e}")
                # Fallback to try local file with same key filename
                filename = path.split("/")[-1]
                filepath = os.path.join(self.local_fallback_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        return f.read()
                raise e
        elif path.startswith("file://"):
            filepath = path[7:]
            with open(filepath, 'rb') as f:
                return f.read()
        else:
            with open(path, 'rb') as f:
                return f.read()
