"""
Users API endpoints - Firebase Firestore implementation
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from backend.models.schemas import (
    UserProfile, UserCreate, UserUpdate, UserList, 
    ChangePasswordRequest, BaseResponse
)
from backend.api.auth import get_current_user, get_admin_user
from backend.services.auth_service import auth_service
from backend.database.firebase_connection import firebase_manager
from datetime import datetime
import uuid

router = APIRouter()

@router.get("/", response_model=UserList)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    setor: Optional[str] = Query(None),
    tipo_usuario: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user)
):
    """
    List all users (admin only) - Firebase implementation
    
    - **page**: Page number (starts from 1)
    - **per_page**: Items per page (max 100)
    - **search**: Search in name or email
    - **setor**: Filter by department
    - **tipo_usuario**: Filter by user type (admin/user)
    """
    try:
        # Build Firebase query filters
        filters = []
        
        if setor:
            filters.append(("setor", "==", setor))
        
        if tipo_usuario:
            filters.append(("tipo_usuario", "==", tipo_usuario))
        
        # Get all users with filters
        result = firebase_manager.query_collection("usuarios", filters=filters, order_by="created_at")
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Database error")
        
        users_data = result.get('data', [])
        
        # Additional filtering for search (name or email) - done in memory
        if search:
            search_lower = search.lower()
            users_data = [
                user for user in users_data
                if (search_lower in user.get('nome', '').lower() or
                    search_lower in user.get('email', '').lower())
            ]
        
        # Manual pagination
        total = len(users_data)
        offset = (page - 1) * per_page
        paginated_users = users_data[offset:offset + per_page]
        
        # Convert to response models
        users = []
        for user_data in paginated_users:
            # Convert Firebase timestamp to datetime if needed
            if 'created_at' in user_data and hasattr(user_data['created_at'], 'timestamp'):
                user_data['created_at'] = datetime.fromtimestamp(user_data['created_at'].timestamp())
            if 'last_login' in user_data and hasattr(user_data['last_login'], 'timestamp'):
                user_data['last_login'] = datetime.fromtimestamp(user_data['last_login'].timestamp())
            
            # Ensure required fields with defaults
            user_data.setdefault('telefone', None)
            user_data.setdefault('cargo', None)
            user_data.setdefault('last_login', None)
            
            users.append(UserProfile(**user_data))
        
        return UserList(
            users=users,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=UserProfile)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_admin_user)
):
    """
    Create new user (admin only) - Firebase implementation
    """
    try:
        # Check if email already exists
        existing_users = firebase_manager.query_collection("usuarios", filters=[("email", "==", user_data.email)])
        
        if existing_users['success'] and existing_users.get('data'):
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = auth_service.hash_password(user_data.senha)
        
        # Prepare user data
        user_doc = {
            "nome": user_data.nome,
            "email": user_data.email,
            "senha_hash": hashed_password,
            "setor": user_data.setor,
            "telefone": user_data.telefone,
            "cargo": user_data.cargo,
            "tipo_usuario": user_data.tipo_usuario,
            "ativo": user_data.ativo,
            "created_at": datetime.now(),
            "last_login": None
        }
        
        # Create user in Firebase
        result = firebase_manager.create_document("usuarios", user_doc)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Prepare response data
        user_doc['id'] = result['id']
        
        # Log action
        auth_service.log_user_action(
            current_user['id'],
            "CREATE_USER",
            f"Created user: {user_data.nome} ({user_data.email})"
        )
        
        return UserProfile(**user_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
          # Log action
        auth_service.log_user_action(
            current_user['id'],
            "CREATE_USER",
            f"Created user: {user_data.nome} ({user_data.email})"
        )
        
        return UserProfile(**user_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user by ID - Firebase implementation
    
    Users can only view their own profile unless they are admin
    """
    # Check permission
    if current_user['tipo_usuario'] != 'admin' and current_user['id'] != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this user"
        )
    
    try:
        result = firebase_manager.get_document("usuarios", user_id)
        
        if not result['success'] or not result.get('data'):
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = result['data']
        
        # Convert Firebase timestamp to datetime if needed
        if 'created_at' in user_data and hasattr(user_data['created_at'], 'timestamp'):
            user_data['created_at'] = datetime.fromtimestamp(user_data['created_at'].timestamp())
        if 'last_login' in user_data and hasattr(user_data['last_login'], 'timestamp'):
            user_data['last_login'] = datetime.fromtimestamp(user_data['last_login'].timestamp())
        
        # Ensure required fields with defaults
        user_data.setdefault('telefone', None)
        user_data.setdefault('cargo', None)
        user_data.setdefault('last_login', None)
        
        return UserProfile(**user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=UserProfile)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user - Firebase implementation
    
    Users can only update their own profile unless they are admin
    """
    # Check permission
    if current_user['tipo_usuario'] != 'admin' and current_user['id'] != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this user"
        )
    
    try:
        # Get current user to verify existence
        current_result = firebase_manager.get_document("usuarios", user_id)
        if not current_result['success'] or not current_result.get('data'):
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build update data
        update_data = {}
        
        if user_data.nome is not None:
            update_data['nome'] = user_data.nome
        
        if user_data.email is not None:
            # Check if email is already used by another user
            existing_users = firebase_manager.query_collection("usuarios", filters=[("email", "==", user_data.email)])
            if existing_users['success'] and existing_users.get('data'):
                for user in existing_users['data']:
                    if user.get('id') != user_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Email already used by another user"
                        )
            
            update_data['email'] = user_data.email
        
        if user_data.setor is not None:
            update_data['setor'] = user_data.setor
        
        if user_data.telefone is not None:
            update_data['telefone'] = user_data.telefone
        
        if user_data.cargo is not None:
            update_data['cargo'] = user_data.cargo
        
        # Only admin can change user type and status
        if current_user['tipo_usuario'] == 'admin':
            if user_data.tipo_usuario is not None:
                update_data['tipo_usuario'] = user_data.tipo_usuario
            
            if user_data.ativo is not None:
                update_data['ativo'] = user_data.ativo
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update timestamp
        update_data['updated_at'] = datetime.now()
        
        # Update user in Firebase
        result = firebase_manager.update_document("usuarios", user_id, update_data)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Failed to update user")
        
        # Get updated user
        updated_result = firebase_manager.get_document("usuarios", user_id)
        if not updated_result['success'] or not updated_result.get('data'):
            raise HTTPException(status_code=500, detail="Failed to retrieve updated user")
        
        updated_user = updated_result['data']
        
        # Convert Firebase timestamp to datetime if needed
        if 'created_at' in updated_user and hasattr(updated_user['created_at'], 'timestamp'):
            updated_user['created_at'] = datetime.fromtimestamp(updated_user['created_at'].timestamp())
        if 'last_login' in updated_user and hasattr(updated_user['last_login'], 'timestamp'):
            updated_user['last_login'] = datetime.fromtimestamp(updated_user['last_login'].timestamp())
        
        # Ensure required fields with defaults
        updated_user.setdefault('telefone', None)
        updated_user.setdefault('cargo', None)
        updated_user.setdefault('last_login', None)
          # Log action
        auth_service.log_user_action(
            current_user['id'],
            "UPDATE_USER",
            f"Updated user: {updated_user.get('nome', 'Unknown')} (ID: {user_id})"
        )
        
        return UserProfile(**updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Delete user (admin only) - Firebase implementation
    """
    if user_id == current_user['id']:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    try:
        # Check if user exists
        result = firebase_manager.get_document("usuarios", user_id)
        
        if not result['success'] or not result.get('data'):
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = result['data']
        user_email = user_data.get('email', 'Unknown')
        
        # Delete user from Firebase
        delete_result = firebase_manager.delete_document("usuarios", user_id)
        
        if not delete_result['success']:
            raise HTTPException(status_code=500, detail="Failed to delete user")
        
        # Log action
        auth_service.log_user_action(
            current_user['id'],
            "DELETE_USER",
            f"Deleted user: {user_email} (ID: {user_id})"
        )
        
        return BaseResponse(
            success=True,
            message="User deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/change-password", response_model=BaseResponse)
async def change_password(
    user_id: str,
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change user password - Firebase implementation
    
    Users can only change their own password unless they are admin
    """
    # Check permission
    if current_user['tipo_usuario'] != 'admin' and current_user['id'] != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to change this user's password"
        )
    
    try:
        # Get user data
        user_result = firebase_manager.get_document("usuarios", user_id)
        if not user_result['success'] or not user_result.get('data'):
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_result['data']
        
        # If not admin, verify current password
        if current_user['tipo_usuario'] != 'admin':
            current_hash = user_data.get('senha_hash', '')
            
            if not auth_service.verify_password(password_data.current_password, current_hash):
                raise HTTPException(
                    status_code=400,
                    detail="Current password is incorrect"
                )
        
        # Hash new password
        new_hash = auth_service.hash_password(password_data.new_password)
        
        # Update password in Firebase
        update_data = {
            'senha_hash': new_hash,
            'updated_at': datetime.now()
        }
        
        result = firebase_manager.update_document("usuarios", user_id, update_data)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Failed to update password")
        
        # Log action
        auth_service.log_user_action(
            current_user['id'],
            "CHANGE_PASSWORD",
            f"Changed password for user ID: {user_id}"
        )
        
        return BaseResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
