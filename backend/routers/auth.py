from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Dict, Any

from models.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse, 
    PasswordReset, PasswordResetConfirm, ChangePassword, RefreshTokenRequest
)
from services.auth_service import auth_service
from db.auth_crud import (
    create_user, get_user_by_email, get_user_by_email_with_login_retry, get_user_by_username, get_user_by_id,
    update_last_login, create_user_session, invalidate_user_session,
    create_password_reset_token, verify_reset_token, 
    mark_reset_token_used, update_user_password
)
from dependencies.auth import get_current_user, get_current_active_user
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/test-signup")
async def test_signup(user_data: UserCreate):
    """Debug endpoint to test data validation"""
    try:
        return {
            "received_data": user_data.dict(), 
            "status": "validation_success",
            "message": "Data validation passed - database tables may be missing"
        }
    except Exception as e:
        return {"error": str(e), "status": "validation_error"}

@router.post("/test-login")
async def test_login(login_data: UserLogin):
    """Debug endpoint to test login data validation"""
    try:
        return {
            "received_data": login_data.dict(), 
            "status": "validation_success",
            "message": "Login data validation passed"
        }
    except Exception as e:
        return {"error": str(e), "status": "validation_error"}

@router.get("/debug/verify-token")
async def debug_verify_token(current_user: dict = Depends(get_current_active_user)):
    """Debug endpoint to verify token is working"""
    return {
        "user_id": current_user.get("id"),
        "email": current_user.get("email"),
        "username": current_user.get("username"),
        "is_active": current_user.get("is_active"),
        "token_valid": True,
        "message": "Token verification successful"
    }

@router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate, request: Request):
    """Register a new user"""
    try:
        # Check if email already exists
        existing_user = await get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        existing_username = await get_user_by_username(user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user_dict = user_data.dict()
        user_dict["is_active"] = True
        user_dict["is_verified"] = False
        created_user = await create_user(user_dict)
        
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Generate tokens
        tokens = auth_service.generate_tokens(created_user)
        
        # Create session
        token_hash = auth_service.hash_token(tokens["refresh_token"])
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        await create_user_session(
            user_id=created_user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None
        )
        
        # Update last login
        await update_last_login(created_user["id"])
        
        return TokenResponse(
            **tokens,
            user=UserResponse(**created_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, request: Request):
    """Login user"""
    try:
        # Check login attempts
        if not auth_service.check_login_attempts(login_data.email):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {settings.LOGIN_ATTEMPT_TIMEOUT_MINUTES} minutes."
            )
        
        # Get user with enhanced retry logic for login
        user = await get_user_by_email_with_login_retry(login_data.email)
        if not user:
            auth_service.record_login_attempt(login_data.email, False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not auth_service.verify_password(login_data.password, user["password_hash"]):
            auth_service.record_login_attempt(login_data.email, False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Record successful login
        auth_service.record_login_attempt(login_data.email, True)
        
        # Generate tokens
        tokens = auth_service.generate_tokens(user)
        
        # Create session
        token_hash = auth_service.hash_token(tokens["refresh_token"])
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        await create_user_session(
            user_id=user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None
        )
        
        # Update last login
        await update_last_login(user["id"])
        
        return TokenResponse(
            **tokens,
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_active_user)):
    """Logout user"""
    try:
        # Note: In a real implementation, you'd need to get the actual token
        # and invalidate the session. For now, we'll just return success.
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(**current_user)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh access token"""
    try:
        # Verify refresh token
        payload = auth_service.verify_token(refresh_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        # Get user
        user = await get_user_by_id(user_id)
        if not user or not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Generate new tokens
        tokens = auth_service.generate_tokens(user)
        
        return TokenResponse(
            **tokens,
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/forgot-password")
async def forgot_password(password_reset: PasswordReset):
    """Request password reset"""
    try:
        user = await get_user_by_email(password_reset.email)
        if not user:
            # Don't reveal if email exists or not
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Generate reset token
        reset_token = auth_service.generate_reset_token()
        token_hash = auth_service.hash_token(reset_token)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        # Save reset token
        await create_password_reset_token(user["id"], token_hash, expires_at)
        
        # TODO: Send email with reset token
        # await send_password_reset_email(user["email"], reset_token)
        
        return {"message": "If the email exists, a reset link has been sent"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset request failed: {str(e)}"
        )

@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    """Reset password with token"""
    try:
        # Verify reset token
        token_hash = auth_service.hash_token(reset_data.token)
        reset_record = await verify_reset_token(token_hash)
        
        if not reset_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Hash new password
        new_password_hash = auth_service.hash_password(reset_data.new_password)
        
        # Update password
        await update_user_password(reset_record["user_id"], new_password_hash)
        
        # Mark token as used
        await mark_reset_token_used(reset_record["id"])
        
        return {"message": "Password successfully reset"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )

@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: dict = Depends(get_current_active_user)
):
    """Change user password"""
    try:
        # Verify current password
        if not auth_service.verify_password(password_data.current_password, current_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = auth_service.hash_password(password_data.new_password)
        
        # Update password
        await update_user_password(current_user["id"], new_password_hash)
        
        return {"message": "Password successfully changed"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )