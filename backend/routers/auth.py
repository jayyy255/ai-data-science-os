from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, UserSession
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SignupRequest(BaseModel):
    full_name: str
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    identity: str
    password: str

class LogoutRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
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
        
    hashed_password = pwd_context.hash(payload.password)
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
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    
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
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Search by email or username
    user = db.query(User).filter(
        (User.email == payload.identity) | (User.username == payload.identity)
    ).first()
    
    if not user or not pwd_context.verify(payload.password, user.password_hash):
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
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    
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
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(UserSession.refresh_token == payload.refresh_token).first()
    if session:
        db.delete(session)
        db.commit()
    return {"status": "success", "message": "Session invalidated successfully"}

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email address not registered"
        )
        
    # Reset password to a standard test value: reset12345
    temp_pass = "reset12345"
    user.password_hash = pwd_context.hash(temp_pass)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Password reset successfully. Your temporary password is: {temp_pass}"
    }
