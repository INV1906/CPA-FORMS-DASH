"""
Firebase Authentication service with JWT tokens and password hashing
"""

import hashlib
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.database.firebase_connection import firebase_manager
from backend.core.config import settings

class FirebaseAuthService:
    """Firebase Authentication service"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return FirebaseAuthService.hash_password(password) == hashed_password
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password using Firebase"""
        try:
            # Get user from Firebase
            result = firebase_manager.query_collection("usuarios", [
                ("email", "==", email),
                ("ativo", "==", True)
            ])
            
            if not result['success'] or not result['data']:
                return None
            
            user = result['data'][0]
            
            # Verify password
            if not FirebaseAuthService.verify_password(password, user['senha_hash']):
                return None
            
            # Update last login
            firebase_manager.update_document("usuarios", user['id'], {
                "ultimo_login": datetime.now()
            })
            
            # Log login
            FirebaseAuthService.log_user_action(user['id'], "LOGIN", f"Login successful for {email}")            # Return user data (without password)
            user_data = {
                'id': user['id'],
                'nome': user['nome'],
                'email': user['email'],
                'tipo_usuario': user.get('tipo_usuario', user.get('cargo', 'user')),  # Priorizar tipo_usuario
                'cargo': user.get('cargo'),  # Incluir campo cargo para compatibilidade
                'setor': user['setor'],
                'ativo': user['ativo'],
                'created_at': user.get('created_at'),
                'last_login': datetime.now()
            }
            
            return user_data
            
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID from Firebase"""
        try:
            result = firebase_manager.get_document("usuarios", user_id)
            
            if not result['success']:
                return None
            
            user = result['data']
            
            if not user.get('ativo', False):
                return None
            
            return {
                'id': user['id'],
                'nome': user['nome'],
                'email': user['email'],
                'tipo_usuario': user['cargo'],  # Mapear cargo para tipo_usuario
                'setor': user['setor'],
                'ativo': user['ativo'],
                'created_at': user.get('created_at'),
                'last_login': user.get('ultimo_login')
            }
            
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user in Firebase"""
        try:
            # Hash password
            if 'password' in user_data:
                user_data['senha_hash'] = FirebaseAuthService.hash_password(user_data['password'])
                del user_data['password']
            
            # Set defaults
            user_data['ativo'] = user_data.get('ativo', True)
            user_data['cargo'] = user_data.get('cargo', 'usuario')
            user_data['ultimo_login'] = None
            
            result = firebase_manager.create_document("usuarios", user_data)
            
            if result['success']:
                FirebaseAuthService.log_user_action(result['id'], "USER_CREATED", f"User created: {user_data['email']}")
                return {"success": True, "user_id": result['id']}
            else:
                return {"success": False, "error": result['error']}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_user(user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user in Firebase"""
        try:
            # Hash password if provided
            if 'password' in user_data:
                user_data['senha_hash'] = FirebaseAuthService.hash_password(user_data['password'])
                del user_data['password']
            
            result = firebase_manager.update_document("usuarios", user_id, user_data)
            
            if result['success']:
                FirebaseAuthService.log_user_action(user_id, "USER_UPDATED", f"User updated: {user_id}")
                return {"success": True}
            else:
                return {"success": False, "error": result['error']}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def log_user_action(user_id: Optional[str], action: str, details: str, 
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log user action to Firebase"""
        try:
            log_data = {
                "user_id": user_id,
                "action": action,
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.now()
            }
            
            firebase_manager.create_document("logs", log_data)
            
        except Exception as e:
            print(f"Error logging user action: {e}")
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token"""
        payload = FirebaseAuthService.verify_token(refresh_token)
        
        if not payload or payload.get('type') != 'refresh':
            return None
        
        user_id = payload.get('sub')
        if not user_id:
            return None
        
        # Create new access token
        access_token_data = {"sub": str(user_id)}
        return FirebaseAuthService.create_access_token(access_token_data)
    
    @staticmethod
    def get_users(filters: Optional[Dict] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Get list of users from Firebase"""
        try:
            firebase_filters = []
            
            if filters:
                for key, value in filters.items():
                    firebase_filters.append((key, "==", value))
            
            result = firebase_manager.query_collection("usuarios", firebase_filters, limit=limit)
            
            if result['success']:
                # Remove sensitive data
                users = []
                for user in result['data']:
                    user_data = user.copy()
                    if 'senha_hash' in user_data:
                        del user_data['senha_hash']
                    user_data['tipo_usuario'] = user_data.get('cargo', 'usuario')
                    users.append(user_data)
                
                return {"success": True, "data": users}
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# Create service instance
firebase_auth_service = FirebaseAuthService()

# Create alias for backward compatibility
auth_service = firebase_auth_service
