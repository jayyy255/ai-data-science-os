"""Run hourly: python scripts/cleanup_uploads.py. Deletes only issued quarantine objects."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.connection import SessionLocal
from database.models import DatasetUpload
from services.storage.factory import get_storage_provider


def cleanup(db, storage):
    # Wait beyond URL expiry; client may replay a valid signed POST until then.
    cutoff = datetime.utcnow() - timedelta(hours=1)
    records = db.query(DatasetUpload).filter(DatasetUpload.expires_at < cutoff).all()
    removed = 0
    for record in records:
        # Paths are server-issued; never accept an arbitrary path on this CLI.
        if storage.delete_file(record.path):
            removed += 1
        if record.status in {'pending', 'validating'}:
            record.status = 'expired'
    db.commit()
    return removed


if __name__ == '__main__':
    with SessionLocal() as db:
        print(f'Removed {cleanup(db, get_storage_provider())} expired quarantine objects')
