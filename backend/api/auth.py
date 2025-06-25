"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
from backend.models.schemas import (
    LoginRequest, LoginResponse, TokenRefreshRequest, 
    UserProfile, BaseResponse
)
from backend.services.auth_service import firebase_auth_service
from backend.core.config import settings

router = APIRouter()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = firebase_auth_service.verify_token(token)
    
    if not payload or payload.get('type') != 'access':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = firebase_auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin user"""
    if current_user.get('tipo_usuario') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Alias para compatibilidade
require_admin = get_admin_user

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, login_data: LoginRequest):
    """
    Authenticate user and return JWT tokens
    
    Returns access token (30 min) and refresh token (7 days)
    """
    # Get client info
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Authenticate user
    user = firebase_auth_service.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        # Log failed attempt
        firebase_auth_service.log_user_action(
            None, "LOGIN_FAILED", 
            f"Failed login attempt for {login_data.email}",
            client_host, user_agent
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens
    token_data = {
        "sub": str(user['id']),
        "email": user['email'],
        "tipo_usuario": user['tipo_usuario']
    }
    access_token = firebase_auth_service.create_access_token(token_data)
    refresh_token = firebase_auth_service.create_refresh_token(token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfile(**user)
    )

@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: TokenRefreshRequest):
    """
    Refresh access token using refresh token
    """
    new_access_token = firebase_auth_service.refresh_access_token(refresh_data.refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile
    """
    return UserProfile(**current_user)

@router.post("/logout", response_model=BaseResponse)
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Logout user (client should discard tokens)
    """
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Log logout
    firebase_auth_service.log_user_action(
        current_user['id'], "LOGOUT", 
        f"User logged out",
        client_host, user_agent
    )
    
    return BaseResponse(
        success=True,
        message="Logged out successfully"
    )

@router.post("/verify", response_model=BaseResponse)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify if token is valid
    """
    return BaseResponse(
        success=True,
        message="Token is valid",
        data={"user_id": current_user['id'], "email": current_user['email']}
    )
