import os
import boto3
from botocore.client import Config
from services.storage.base import StorageProvider

class MinIOStorage(StorageProvider):
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "password123")
        
        self.bucket_name = "aidso-runs"
        self.local_fallback_dir = "./tmp/minio_fallback"
        os.makedirs(self.local_fallback_dir, exist_ok=True)
        
        try:
            self.s3 = boto3.client(
                's3',
                endpoint_url=f"http://{endpoint}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            # Ensure bucket exists
            self.s3.create_bucket(Bucket=self.bucket_name)
            self.client_enabled = True
        except Exception as e:
            print(f"MinIO client initialization failed (falling back to local directories): {e}")
            self.client_enabled = False

    def upload_dataset(self, filename: str, content: bytes) -> str:
        key = f"datasets/{filename}"
        if self.client_enabled:
            try:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content
                )
                return f"s3://{self.bucket_name}/{key}"
            except Exception as e:
                print(f"Failed uploading to MinIO: {e}")
        
        # Fallback
        filepath = os.path.join(self.local_fallback_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return f"file://{os.path.abspath(filepath)}"

    def upload_model(self, project_id: str, model_type: str, content: bytes) -> str:
        key = f"models/{project_id}/{model_type}.pkl"
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
        
        # Fallback
        filepath = os.path.join(self.local_fallback_dir, f"{project_id}_{model_type}.pkl")
        with open(filepath, 'wb') as f:
            f.write(content)
        return f"file://{os.path.abspath(filepath)}"

    def upload_report(self, filename: str, content: bytes) -> str:
        key = f"reports/{filename}"
        if self.client_enabled:
            try:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content
                )
                return f"s3://{self.bucket_name}/{key}"
            except Exception as e:
                print(f"Failed uploading report to MinIO: {e}")
        
        # Fallback
        filepath = os.path.join(self.local_fallback_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return f"file://{os.path.abspath(filepath)}"

    def upload_shap(self, filename: str, content: bytes) -> str:
        key = f"shap/{filename}"
        if self.client_enabled:
            try:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content
                )
                return f"s3://{self.bucket_name}/{key}"
            except Exception as e:
                print(f"Failed uploading SHAP to MinIO: {e}")
        
        # Fallback
        filepath = os.path.join(self.local_fallback_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return f"file://{os.path.abspath(filepath)}"

    def download_file(self, path: str) -> bytes:
        if path.startswith("s3://"):
            try:
                bucket_and_key = path[5:]
                bucket, key = bucket_and_key.split("/", 1)
                response = self.s3.get_object(Bucket=bucket, Key=key)
                return response['Body'].read()
            except Exception as e:
                print(f"MinIO download failed: {e}")
                # Try fallback folder
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

    def delete_file(self, path: str) -> bool:
        if path.startswith("s3://"):
            try:
                bucket_and_key = path[5:]
                bucket, key = bucket_and_key.split("/", 1)
                self.s3.delete_object(Bucket=bucket, Key=key)
                return True
            except Exception as e:
                print(f"MinIO delete failed: {e}")
                return False
        elif path.startswith("file://"):
            filepath = path[7:]
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        return False

    def generate_presigned_upload_url(self, filename: str) -> dict:
        key = f"datasets/{filename}"
        if self.client_enabled:
            try:
                url = self.s3.generate_presigned_url(
                    ClientMethod='put_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=3600
                )
                return {
                    "url": url,
                    "method": "PUT",
                    "fields": {},
                    "s3_path": f"s3://{self.bucket_name}/{key}"
                }
            except Exception as e:
                print(f"Failed generating MinIO presigned upload URL: {e}")
        
        # Fallback simulating direct upload URL pointing to the dev server upload endpoint
        return {
            "url": f"http://localhost:8000/api/projects/upload-local?filename={filename}",
            "method": "POST",
            "fields": {},
            "s3_path": f"file://{os.path.abspath(os.path.join(self.local_fallback_dir, filename))}"
        }

    def generate_presigned_download_url(self, path: str) -> str:
        if path.startswith("s3://"):
            bucket_and_key = path[5:]
            bucket, key = bucket_and_key.split("/", 1)
            if self.client_enabled:
                try:
                    url = self.s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=3600
                    )
                    return url
                except Exception as e:
                    print(f"Failed generating MinIO presigned download URL: {e}")
        
        # Fallback to local files via proxy
        if path.startswith("file://"):
            filename = os.path.basename(path)
            return f"http://localhost:8000/api/projects/download-local-file?filename={filename}"
            
        return path
