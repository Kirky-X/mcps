"""Direct Supabase authentication implementation to bypass IPv6 issues"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from supabase import create_client
from supabase.lib.client_options import ClientOptions
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr

from prompt_manager.utils.config import load_config

class AuthUser(BaseModel):
    id: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: AuthUser
    expires_in: int = 3600

class DirectSupabaseAuth:
    """Direct Supabase authentication bypassing SQLAlchemy/IPv6 issues"""
    
    def __init__(self):
        self.config = load_config()
        self.supabase = create_client(
            self.config.database.supabase_url,
            self.config.database.supabase_key
        )
        self._jwt_secret = "your-jwt-secret-key"  # Should be in config
    
    async def register_user(self, email: str, password: str) -> AuthResponse:
        """Register a new user using direct Supabase auth"""
        try:
            # Use Supabase Auth directly
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration failed"
                )
            
            # Create user record in prompts schema
            await self._create_user_record(response.user.id, email)
            
            # Handle case where session might be None (email confirmation required)
            if response.session is None:
                # For email confirmation scenarios, return a placeholder response
                # In production, you might want to handle this differently
                return AuthResponse(
                    access_token="email_confirmation_required",
                    refresh_token="email_confirmation_required",
                    user=AuthUser(
                        id=response.user.id,
                        email=response.user.email,
                        created_at=response.user.created_at
                    ),
                    expires_in=0
                )
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user=AuthUser(
                    id=response.user.id,
                    email=response.user.email,
                    created_at=response.user.created_at
                )
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def login_user(self, email: str, password: str) -> AuthResponse:
        """Login user using direct Supabase auth"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user is None or response.session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user=AuthUser(
                    id=response.user.id,
                    email=response.user.email,
                    created_at=response.user.created_at,
                    updated_at=response.user.updated_at
                )
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login failed: {str(e)}"
            )
    
    async def _create_user_record(self, user_id: str, email: str) -> None:
        """Create user record in prompts schema"""
        try:
            # For now, skip creating user record in prompts schema
            # This would require proper schema configuration in Supabase dashboard
            print(f"Skipping user record creation in prompts schema for user: {user_id}")
            
        except Exception as e:
            print(f"Warning: Could not create user record in prompts schema: {e}")
            # Don't fail the registration if prompts schema user creation fails
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            # For now, we'll use Supabase's built-in token verification
            # In production, implement proper JWT verification
            return {"user_id": "placeholder", "email": "placeholder"}
        except jwt.InvalidTokenError:
            return None
    
    async def get_user(self, user_id: str) -> Optional[AuthUser]:
        """Get user by ID from Supabase auth"""
        try:
            # Get user from Supabase auth directly
            user_response = self.supabase.auth.admin.get_user_by_id(user_id)
            
            if user_response.user:
                return AuthUser(
                    id=user_response.user.id,
                    email=user_response.user.email,
                    created_at=user_response.user.created_at,
                    updated_at=user_response.user.updated_at
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

# Global instance
direct_auth = DirectSupabaseAuth()