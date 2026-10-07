import io
import pandas as pd

def validate_csv_content(content: bytes):
    """
    Validates that the file has text/CSV magic bytes and parses the first 50 rows 
    successfully using Pandas to ensure proper CSV structure.
    """
    if not content:
        raise ValueError("File content is empty")
        
    # Check magic bytes for common binary signatures
    magic = content[:4]
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
        pd.read_csv(io.BytesIO(content), nrows=50)
    except Exception as e:
        raise ValueError(f"File content could not be parsed as CSV: {e}")

def scan_file_for_virus(content: bytes) -> bool:
    """
    Simulates an antivirus scanning pipeline.
    Checks for the standard EICAR anti-virus test file signature.
    Returns True if clean, False if infected.
    """
    # EICAR Standard Antivirus Test File signature
    eicar_sig = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
    if eicar_sig in content:
        return False
        
    # Simulated scanning delay
    import time
    time.sleep(0.3)
    return True


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

