"""Quarantine/security tests; optional real ClamAV integration."""
import io
import os
import socket
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from database.models import Base, User, DatasetUpload
from services import uploads
from services.security import scan_file_for_virus, ScannerUnavailable


class UploadSecurityTests(unittest.TestCase):
    def setUp(self):
        Path('tmp').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=Path('tmp').resolve())
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add(User(username='owner', email='owner@test', full_name='Owner', password_hash='unused'))
        self.db.commit()
        self.storage = MagicMock()
        self.storage.upload_signing_client = None
        self.storage.client = None
        self.storage.client_enabled = False
        self.storage.local_fallback_dir = self.tmp.name
        self.storage.delete_file.side_effect = lambda path: Path(path[7:]).unlink(missing_ok=True) or True
        self.storage.upload_dataset.return_value = 'file://approved.csv'

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.tmp.cleanup()

    def reserve(self):
        return uploads.reserve(self.storage, self.db, 'owner', 'data.csv')

    def test_signed_post_restricts_exact_key_type_size_and_expiry(self):
        self.storage.client = MagicMock()
        self.storage.bucket_name = 'private'
        self.storage.client.generate_presigned_post.return_value = {'url': 'https://storage', 'fields': {}}
        record, result = self.reserve()
        args = self.storage.client.generate_presigned_post.call_args.kwargs
        self.assertEqual(args['Key'], 'quarantine/' + record.id + '.csv')
        self.assertEqual(args['Conditions'], [['content-length-range', 1, 50*1024*1024], {'Content-Type': 'text/csv'}])
        self.assertEqual(args['ExpiresIn'], 900)
        self.assertEqual(result['method'], 'POST')

    def test_ownership_expiry_and_arbitrary_paths(self):
        record, _ = self.reserve()
        for username, path in [('other', record.path), ('owner', 's3://anything/datasets/owner_fake.csv')]:
            with self.assertRaises(HTTPException):
                uploads.owned_upload(self.db, username, path=path)
        record.expires_at = datetime.utcnow() - timedelta(seconds=1)
        self.db.commit()
        with self.assertRaises(HTTPException):
            uploads.owned_upload(self.db, 'owner', path=record.path)

    def test_approval_publishes_scanned_bytes_and_cannot_be_reused(self):
        record, _ = self.reserve()
        content = b'age,target\n1,yes\n2,no\n'
        uploads.stage(self.storage, record, content)
        with patch('services.uploads.scan_file_for_virus', return_value=True) as scan, patch('services.uploads.validate_csv_content'), patch('services.dataset.DatasetService.profile_dataset', return_value={'rows_count': 2, 'columns_count': 2}):
            uploads.validate_upload(self.storage, self.db, record, 'target', 'auto')
        scan.assert_called_once_with(content)
        self.assertEqual(self.storage.upload_dataset.call_args.args[1], content)
        self.assertEqual(record.status, 'approved')
        self.assertEqual(len(record.sha256), 64)
        self.assertFalse(Path(record.path[7:]).exists())
        with self.assertRaises(HTTPException):
            uploads.validate_upload(self.storage, self.db, record, 'target', 'auto')

    def test_malware_and_scanner_outage_never_publish(self):
        for failure in (False, ScannerUnavailable('offline')):
            record, _ = self.reserve()
            uploads.stage(self.storage, record, b'x,target\n1,0')
            with patch('services.uploads.scan_file_for_virus', side_effect=failure if isinstance(failure, Exception) else None, return_value=False):
                with self.assertRaises((HTTPException, ScannerUnavailable)):
                    uploads.validate_upload(self.storage, self.db, record, 'target', 'auto')
            self.assertEqual(record.status, 'rejected')
            self.assertFalse(Path(record.path[7:]).exists())
        self.storage.upload_dataset.assert_not_called()

    def test_row_limit_and_format_failure_never_publish(self):
        for profile in ({'rows_count': 100001, 'columns_count': 2}, {'rows_count': 10, 'columns_count': 201}):
            record, _ = self.reserve()
            uploads.stage(self.storage, record, b'x,target\n1,0')
            with patch('services.uploads.scan_file_for_virus', return_value=True), patch('services.uploads.validate_csv_content'), patch('services.dataset.DatasetService.profile_dataset', return_value=profile):
                with self.assertRaises(HTTPException):
                    uploads.validate_upload(self.storage, self.db, record, 'target', 'auto')
        self.storage.upload_dataset.assert_not_called()

    def test_bounded_s3_read_and_close(self):
        self.storage.client = MagicMock()
        self.storage.bucket_name = 'private'
        self.storage.client.head_object.return_value = {'ContentLength': uploads.MAX_BYTES + 1}
        record, _ = self.reserve()
        with self.assertRaises(HTTPException):
            uploads.read_quarantine(self.storage, record)
        self.storage.client.get_object.assert_not_called()
        self.storage.client.head_object.return_value = {'ContentLength': 5}
        body = MagicMock()
        body.read.return_value = b'hello'
        self.storage.client.get_object.return_value = {'Body': body}
        self.assertEqual(uploads.read_quarantine(self.storage, record), b'hello')
        body.read.assert_called_once_with(uploads.MAX_BYTES + 1)
        body.close.assert_called_once()

    def test_scanner_protocol_requires_explicit_clean_reply(self):
        with patch.dict(os.environ, {'AIDSO_MALWARE_SCANNER': 'clamav'}):
            for reply, outcome in [(b'stream: OK\0', True), (b'stream: Test FOUND\0', False), (b'stream: size limit exceeded ERROR\0', None), (b'', None)]:
                client = MagicMock()
                client.__enter__.return_value = client
                client.recv.return_value = reply
                with patch('socket.create_connection', return_value=client):
                    if outcome is None:
                        with self.assertRaises(ScannerUnavailable): scan_file_for_virus(b'test')
                    else:
                        self.assertEqual(scan_file_for_virus(b'test'), outcome)
                    self.assertEqual(client.sendall.call_args_list[0].args[0], b'zINSTREAM\0')
            with patch('socket.create_connection', side_effect=socket.timeout):
                with self.assertRaises(ScannerUnavailable): scan_file_for_virus(b'test')

    def test_explicit_production_bypass_skips_scanner_but_preserves_csv_validation(self):
        content = b'x,target\n1,yes\n2,no'
        with patch.dict(os.environ, {'ENVIRONMENT': 'production', 'AIDSO_MALWARE_SCANNER': 'bypass'}), patch('socket.create_connection') as network:
            self.assertTrue(scan_file_for_virus(content))
            record, _ = self.reserve()
            uploads.stage(self.storage, record, content)
            with patch('services.uploads.validate_csv_content') as validate, patch('services.dataset.DatasetService.profile_dataset', return_value={'rows_count': 2, 'columns_count': 2}):
                _, profile = uploads.validate_upload(self.storage, self.db, record, 'target', 'auto')
            validate.assert_called_once_with(content)
            self.assertEqual(record.scan_engine, 'bypass')
            self.assertEqual(profile['upload_security']['malware_scan'], 'skipped')
            network.assert_not_called()
            second, _ = self.reserve()
            uploads.stage(self.storage, second, content)
            with patch('services.uploads.validate_csv_content', side_effect=ValueError('Invalid CSV')):
                with self.assertRaises(ValueError):
                    uploads.validate_upload(self.storage, self.db, second, 'target', 'auto')
            self.assertEqual(second.status, 'rejected')
            self.assertEqual(self.storage.upload_dataset.call_count, 1)

    def test_production_cannot_disable_scanner(self):
        with patch.dict(os.environ, {'ENVIRONMENT': 'production', 'AIDSO_MALWARE_SCANNER': 'development'}):
            with self.assertRaises(ScannerUnavailable): scan_file_for_virus(b'clean')

    @unittest.skipUnless(os.getenv('AIDSO_TEST_OBJECT_STORE') == '1', 'Real object-store integration opt-in')
    def test_real_object_store_enforces_post_policy(self):
        import boto3
        import httpx
        import uuid
        from botocore.client import Config
        client = boto3.client('s3', endpoint_url=os.environ['TEST_OBJECT_STORE_URL'],
            aws_access_key_id='admin', aws_secret_access_key='password123',
            region_name='us-east-1', config=Config(signature_version='s3v4'))
        bucket = 'upload-policy-test-' + uuid.uuid4().hex
        client.create_bucket(Bucket=bucket)
        self.storage.client = client
        self.storage.bucket_name = bucket
        try:
            with patch('services.uploads.MAX_BYTES', 64):
                record, signed = self.reserve()
            def post(content, fields=None):
                return httpx.post(signed['url'], data=fields or signed['fields'],
                    files={'file': ('dataset.csv', content, 'text/csv')}, timeout=15)
            self.assertIn(post(b'x,target\n1,yes').status_code, (200, 204))
            self.assertGreaterEqual(post(b'x' * 65).status_code, 400)
            self.assertGreaterEqual(post(b'x', {**signed['fields'], 'key': 'datasets/bypass.csv'}).status_code, 400)
            self.assertGreaterEqual(post(b'x', {**signed['fields'], 'Content-Type': 'application/octet-stream'}).status_code, 400)
        finally:
            for item in client.list_objects_v2(Bucket=bucket).get('Contents', []):
                client.delete_object(Bucket=bucket, Key=item['Key'])
            client.delete_bucket(Bucket=bucket)

    @unittest.skipUnless(os.getenv('AIDSO_TEST_CLAMAV') == '1', 'Real ClamAV integration opt-in')
    def test_real_clamav_clean_and_eicar(self):
        with patch.dict(os.environ, {'AIDSO_MALWARE_SCANNER': 'clamav'}):
            self.assertTrue(scan_file_for_virus(b'x,target\n1,yes\n2,no\n'))
            eicar = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
            self.assertFalse(scan_file_for_virus(eicar))
