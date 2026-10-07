from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, UserSession
from pydantic import BaseModel
from datetime import datetime, timedelta
import bcrypt
import uuid
import os
import re
from typing import Optional
from services.security import get_optional_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

class SignupRequest(BaseModel):
    full_name: str
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    identity: str
    password: str

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

def set_session_cookies(response: Response, token: str):
    response.set_cookie(
        key="reviewer.sid",
        value=token,
        max_age=14 * 24 * 60 * 60,
        httponly=True,
        samesite="none" if os.getenv('ENVIRONMENT', 'local') != 'local' else 'lax',
        secure=os.getenv('ENVIRONMENT', 'local') != 'local'
    )
    response.set_cookie(
        key="aidso.sid",
        value=token,
        max_age=14 * 24 * 60 * 60,
        httponly=True,
        samesite="none" if os.getenv('ENVIRONMENT', 'local') != 'local' else 'lax',
        secure=os.getenv('ENVIRONMENT', 'local') != 'local'
    )

@router.get("/me")
def get_me(current_user: Optional[User] = Depends(get_optional_current_user)):
    if not current_user:
        return {"user": None}
    return {
        "user": {
            "email": current_user.email,
            "username": current_user.username,
            "fullName": current_user.full_name
        }
    }

@router.post("/signup")
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    if not payload.username.strip() or not payload.full_name.strip() or '@' not in payload.email:
        raise HTTPException(status_code=400, detail='A name, username, and valid email are required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{2,63}', payload.username):
        raise HTTPException(status_code=400, detail='Username must be 3–64 letters, numbers, dots, underscores, or hyphens')
    if not 8 <= len(payload.password.encode('utf-8')) <= 72:
        raise HTTPException(status_code=400, detail='Password must be between 8 and 72 bytes')
    # Check if username exists
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )
        
    # Check if email exists
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
        
    hashed_password = hash_password(payload.password)
    new_user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    
    # Generate tokens directly after signup to log them in
    access_token = str(uuid.uuid4())
    refresh_token = str(uuid.uuid4())
    
    # Save session
    session = UserSession(
        username=new_user.username,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=14)
    )
    db.add(session)
    db.commit()
    
    set_session_cookies(response, refresh_token)
    
    # Store in cache
    from services.security import cache_service
    cache_service.set(f"session:{refresh_token}", new_user.username, expire_seconds=14*24*60*60)
    
    return {
        "status": "success",
        "user": {
            "email": new_user.email,
            "username": new_user.username,
            "fullName": new_user.full_name
        },
        "accessToken": access_token,
        "refreshToken": refresh_token
    }

@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    # Search by email or username
    user = db.query(User).filter(
        (User.email == payload.identity) | (User.username == payload.identity)
    ).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password"
        )
        
    # Generate tokens
    access_token = str(uuid.uuid4())
    refresh_token = str(uuid.uuid4())
    
    # Save session
    session = UserSession(
        username=user.username,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=14)
    )
    db.add(session)
    db.commit()
    
    set_session_cookies(response, refresh_token)
    
    # Store in cache
    from services.security import cache_service
    cache_service.set(f"session:{refresh_token}", user.username, expire_seconds=14*24*60*60)
    
    return {
        "status": "success",
        "user": {
            "email": user.email,
            "username": user.username,
            "fullName": user.full_name
        },
        "accessToken": access_token,
        "refreshToken": refresh_token
    }

@router.post("/logout")
def logout(
    response: Response,
    payload: Optional[LogoutRequest] = None,
    cookie_reviewer_sid: Optional[str] = Cookie(None, alias="reviewer.sid"),
    cookie_aidso_sid: Optional[str] = Cookie(None, alias="aidso.sid"),
    db: Session = Depends(get_db)
):
    token = None
    if payload and payload.refresh_token:
        token = payload.refresh_token
    elif cookie_reviewer_sid:
        token = cookie_reviewer_sid
    elif cookie_aidso_sid:
        token = cookie_aidso_sid
        
    if token:
        session = db.query(UserSession).filter(UserSession.refresh_token == token).first()
        if session:
            db.delete(session)
            db.commit()
        # Delete from cache
        from services.security import cache_service
        if cache_service.redis_enabled:
            try:
                cache_service.client.delete(f"session:{token}")
            except Exception:
                pass
        else:
            cache_service.in_memory_fallback.pop(f"session:{token}", None)
            
    response.delete_cookie(key="reviewer.sid")
    response.delete_cookie(key="aidso.sid")
    return {"status": "success", "success": True, "message": "Logged out successfully"}

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=503, detail='Password recovery is not configured. Contact your administrator; your password has not been changed.')
