import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from config import settings

class AuthService:
    def __init__(self):
        # Use bcrypt with specific configuration to avoid version issues
        self.pwd_context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__rounds=12
        )
        self.login_attempts: Dict[str, Dict[str, Any]] = {}
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        # BCrypt has a 72-byte limit, truncate if necessary
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        # BCrypt has a 72-byte limit, truncate if necessary
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_tokens(self, user_data: dict) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        now = datetime.utcnow()
        
        # Access token (short-lived)
        access_payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "username": user_data["username"],
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        
        # Refresh token (long-lived)
        refresh_payload = {
            "sub": user_data["id"],
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        }
        
        access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def check_login_attempts(self, email: str) -> bool:
        """Check if user has exceeded login attempts"""
        now = datetime.utcnow()
        
        if email in self.login_attempts:
            attempt_data = self.login_attempts[email]
            
            # Reset attempts if timeout period has passed
            if now > attempt_data["timeout_until"]:
                del self.login_attempts[email]
                return True
            
            # Check if max attempts exceeded
            if attempt_data["count"] >= settings.MAX_LOGIN_ATTEMPTS:
                return False
        
        return True
    
    def record_login_attempt(self, email: str, success: bool):
        """Record a login attempt"""
        now = datetime.utcnow()
        
        if success:
            # Remove failed attempts on successful login
            if email in self.login_attempts:
                del self.login_attempts[email]
        else:
            # Record failed attempt
            if email not in self.login_attempts:
                self.login_attempts[email] = {"count": 0, "timeout_until": now}
            
            self.login_attempts[email]["count"] += 1
            self.login_attempts[email]["timeout_until"] = now + timedelta(
                minutes=settings.LOGIN_ATTEMPT_TIMEOUT_MINUTES
            )
    
    def generate_reset_token(self) -> str:
        """Generate a secure reset token"""
        return secrets.token_urlsafe(32)
    
    def hash_token(self, token: str) -> str:
        """Hash a token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()

# Create global instance
auth_service = AuthService()