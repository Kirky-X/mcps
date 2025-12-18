"""Direct Supabase authentication router - bypasses IPv6/SQLAlchemy issues"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from prompt_manager.auth.direct_auth import direct_auth, AuthResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    message: str

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user using direct Supabase authentication"""
    try:
        result = await direct_auth.register_user(request.email, request.password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
        )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user using direct Supabase authentication"""
    try:
        result = await direct_auth.login_user(request.email, request.password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """Get current user info (placeholder - implement proper auth)"""
    # This is a placeholder - implement proper JWT token validation
    return UserResponse(
        id="placeholder-id",
        email="user@example.com",
        message="Implement proper JWT token validation"
    )

@router.post("/logout")
async def logout():
    """Logout user (placeholder - implement proper logout)"""
    # This is a placeholder - implement proper logout
    return {"message": "Logged out successfully (placeholder)"}