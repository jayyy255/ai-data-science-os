
def validate_csv_content(content: bytes):
    """
    Validates that the file has text/CSV magic bytes and parses the first 50 rows 
    successfully using Pandas to ensure proper CSV structure.
    """
    if not content:
        raise ValueError("File content is empty")
        
    # Check magic bytes for common binary signatures
    binary_signatures = {
        b"\x89PNG": "PNG Image",
        b"GIF8": "GIF Image",
        b"PK\x03\x04": "ZIP/Archive/Jar",
        b"\x7fELF": "ELF Executable",
        b"%PDF": "PDF Document",
        b"\xff\xd8\xff": "JPEG Image"
    }
    
    for sig, name in binary_signatures.items():
        if content.startswith(sig):
            raise ValueError(f"Invalid file format: Detected {name} binary signature instead of CSV text")

    # Verify first 50 rows can be parsed as a valid CSV
    try:
        from services.sandbox import run_operation
        run_operation('validate_csv', {}, {'dataset.csv': content})
    except ValueError as e:
        raise ValueError(f"File content could not be parsed as CSV: {e}")

class ScannerUnavailable(RuntimeError):
    pass


def scan_file_for_virus(content: bytes) -> bool:
    """ClamAV INSTREAM, with an explicit operator-selected temporary bypass."""
    import os
    import socket
    import struct
    mode = os.getenv('AIDSO_MALWARE_SCANNER', 'clamav')
    if mode == 'bypass':
        # Temporary deployment setting; never silently fall back on scanner failure.
        return True
    if mode == 'development':
        if os.getenv('ENVIRONMENT', 'local') != 'local':
            raise ScannerUnavailable('Development malware checks are forbidden in production')
        return b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE' not in content
    if mode != 'clamav':
        raise ScannerUnavailable('Invalid malware scanner configuration')
    try:
        with socket.create_connection((os.getenv('CLAMAV_HOST', '127.0.0.1'), int(os.getenv('CLAMAV_PORT', '3310'))), timeout=60) as client:
            client.sendall(b'zINSTREAM\0')
            for offset in range(0, len(content), 65536):
                chunk = content[offset:offset + 65536]
                client.sendall(struct.pack('!I', len(chunk)) + chunk)
            client.sendall(struct.pack('!I', 0))
            reply = bytearray()
            while len(reply) < 4096:
                chunk = client.recv(1024)
                if not chunk:
                    break
                reply.extend(chunk)
                if b'\0' in chunk or b'\n' in chunk:
                    break
        response = bytes(reply).rstrip(b'\0\n')
        if response == b'stream: OK':
            return True
        if response.startswith(b'stream: ') and response.endswith(b' FOUND'):
            return False
        raise ScannerUnavailable('Malware scanner did not confirm a clean file')
    except (OSError, ValueError) as error:
        raise ScannerUnavailable('Malware scanner unavailable; upload has not been approved') from error


from fastapi import Cookie, Header, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, UserSession
from services.cache import RedisCacheService
from datetime import datetime
from typing import Optional

cache_service = RedisCacheService()

def get_session_token(
    authorization: Optional[str] = Header(None),
    cookie_reviewer_sid: Optional[str] = Cookie(None, alias="reviewer.sid"),
    cookie_aidso_sid: Optional[str] = Cookie(None, alias="aidso.sid")
) -> Optional[str]:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]
    if cookie_reviewer_sid:
        return cookie_reviewer_sid
    if cookie_aidso_sid:
        return cookie_aidso_sid
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    return None

def get_optional_current_user(
    token: Optional[str] = Depends(get_session_token),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    
    session = db.query(UserSession).filter(
        UserSession.refresh_token == token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    if not session:
        return None
    username = session.username

    user = db.query(User).filter(User.username == username).first()
    return user

def get_current_user(
    user: Optional[User] = Depends(get_optional_current_user)
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Please log in."
        )
    return user

