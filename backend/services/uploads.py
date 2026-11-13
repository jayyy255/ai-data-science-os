"""Private quarantine, bounded reads, and single-use upload reservations."""
import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from fastapi import HTTPException
from database.models import DatasetUpload
from services.security import scan_file_for_virus, validate_csv_content

MAX_BYTES = 50 * 1024 * 1024
TTL_SECONDS = 900


def client_for(storage):
    return getattr(storage, 'client', None) or (storage.s3 if getattr(storage, 'client_enabled', False) else None)


def reserve(storage, db, username, filename):
    filename = filename.replace('\\', '/').split('/')[-1]
    if not filename.lower().endswith('.csv'):
        raise HTTPException(400, 'Only CSV files are allowed')
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)[-180:]
    recent = db.query(DatasetUpload).filter(DatasetUpload.username == username,
        DatasetUpload.created_at > datetime.utcnow() - timedelta(hours=1)).count()
    if recent >= 50:
        raise HTTPException(429, 'Upload limit reached; please try again later')
    upload_id = uuid.uuid4().hex
    key = f'quarantine/{upload_id}.csv'
    client = client_for(storage)
    path = f's3://{storage.bucket_name}/{key}' if client else 'file://' + str((Path(storage.local_fallback_dir).resolve() / key))
    record = DatasetUpload(id=upload_id, username=username, filename=filename, path=path,
                           expires_at=datetime.utcnow() + timedelta(seconds=TTL_SECONDS))
    db.add(record)
    db.commit()
    if client:
        signing_client = getattr(storage, 'upload_signing_client', None) or client
        signed = signing_client.generate_presigned_post(Bucket=storage.bucket_name, Key=key,
            Fields={'Content-Type': 'text/csv'},
            Conditions=[['content-length-range', 1, MAX_BYTES], {'Content-Type': 'text/csv'}],
            ExpiresIn=TTL_SECONDS)
        response = {**signed, 'method': 'POST'}
    else:
        response = {'url': '/api/projects/upload-local?filename=' + quote(upload_id), 'method': 'POST', 'fields': {}}
    return record, {**response, 's3_path': path, 'upload_id': upload_id, 'max_bytes': MAX_BYTES, 'expires_in': TTL_SECONDS}


def owned_upload(db, username, path=None, upload_id=None):
    query = db.query(DatasetUpload).filter(DatasetUpload.username == username,
        DatasetUpload.status == 'pending', DatasetUpload.expires_at > datetime.utcnow())
    record = query.filter(DatasetUpload.id == upload_id).first() if upload_id else query.filter(DatasetUpload.path == path).first()
    if not record:
        raise HTTPException(400, 'Upload is unknown, expired, already used, or belongs to another user')
    return record


def stage(storage, record, content):
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(400, 'Dataset must contain between 1 byte and 50MB')
    client = client_for(storage)
    if client:
        client.put_object(Bucket=storage.bucket_name, Key='quarantine/' + record.id + '.csv', Body=content, ContentType='text/csv')
    else:
        path = Path(record.path[7:])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def read_quarantine(storage, record):
    client = client_for(storage)
    if client:
        key = 'quarantine/' + record.id + '.csv'
        if client.head_object(Bucket=storage.bucket_name, Key=key)['ContentLength'] > MAX_BYTES:
            raise HTTPException(400, 'Maximum dataset size is 50MB')
        body = client.get_object(Bucket=storage.bucket_name, Key=key)['Body']
        try:
            content = body.read(MAX_BYTES + 1)
        finally:
            body.close()
    else:
        with open(record.path[7:], 'rb') as stream:
            content = stream.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(400, 'Dataset must contain between 1 byte and 50MB')
    return content


def validate_upload(storage, db, record, target, problem_type):
    # Atomic claim prevents two requests from consuming the same reservation.
    claimed = db.query(DatasetUpload).filter(DatasetUpload.id == record.id,
        DatasetUpload.status == 'pending', DatasetUpload.expires_at > datetime.utcnow()).update({'status': 'validating'})
    db.commit()
    if not claimed:
        raise HTTPException(409, 'Upload is already being processed')
    published_path = None
    try:
        content = read_quarantine(storage, record)
        if not scan_file_for_virus(content):
            raise HTTPException(400, 'Dataset rejected by malware scanner')
        validate_csv_content(content)
        from services.dataset import DatasetService
        profile = DatasetService.profile_dataset(content, target, problem_type)
        profile['upload_security'] = {'malware_scan': 'skipped' if os.getenv('AIDSO_MALWARE_SCANNER', 'clamav') == 'bypass' else 'development_check' if os.getenv('AIDSO_MALWARE_SCANNER', 'clamav') == 'development' else 'passed', 'scanner_mode': os.getenv('AIDSO_MALWARE_SCANNER', 'clamav')}
        if profile['rows_count'] > 100000 or profile['columns_count'] > 200:
            raise HTTPException(400, 'Dataset exceeds 100,000 rows or 200 columns')
        # Publish the exact validated bytes, never a mutable object-store copy.
        path = storage.upload_dataset(f'{record.username}_{uuid.uuid4().hex}_{record.filename}', content)
        published_path = path
        record.approved_path = path
        record.status = 'approved'
        record.sha256 = hashlib.sha256(content).hexdigest()
        record.scan_engine = os.getenv('AIDSO_MALWARE_SCANNER', 'clamav')
        record.validated_at = datetime.utcnow()
        db.commit()
        return path, profile
    except Exception:
        db.rollback()
        if published_path:
            storage.delete_file(published_path)
        record.approved_path = None
        record.status = 'rejected'
        db.commit()
        raise
    finally:
        storage.delete_file(record.path)
