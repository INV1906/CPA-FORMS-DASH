"""
Data models using Pydantic for API serialization
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class UserType(str, Enum):
    ADMIN = "admin"
    USER = "user"

class SuggestionStatus(str, Enum):
    PENDING = "pendente"
    IN_REVIEW = "em_analise"
    APPROVED = "aprovada"
    REJECTED = "rejeitada"
    IMPLEMENTED = "implementada"

class Priority(str, Enum):
    LOW = "baixa"
    MEDIUM = "media"
    HIGH = "alta"
    URGENT = "urgente"

# Base Models
class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# Authentication Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: 'UserProfile'

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# User Models
class UserBase(BaseModel):
    nome: str
    email: EmailStr
    setor: str
    telefone: Optional[str] = None
    cargo: Optional[str] = None

class UserCreate(UserBase):
    senha: str
    tipo_usuario: UserType = UserType.USER
    ativo: bool = True

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    setor: Optional[str] = None
    telefone: Optional[str] = None
    cargo: Optional[str] = None
    tipo_usuario: Optional[UserType] = None
    ativo: Optional[bool] = None

class UserProfile(UserBase):
    id: str  # Firebase usa strings como IDs
    tipo_usuario: UserType
    cargo: Optional[str] = None  # Compatibilidade com campo cargo
    ativo: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserList(BaseModel):
    users: List[UserProfile]
    total: int
    page: int
    per_page: int

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

# Suggestion Models
class SuggestionBase(BaseModel):
    titulo: str
    descricao: str
    setor_origem: str
    setor_destino: str
    prioridade: Priority = Priority.MEDIUM

class SuggestionCreate(SuggestionBase):
    pass

class SuggestionUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[SuggestionStatus] = None
    prioridade: Optional[Priority] = None
    setor_destino: Optional[str] = None
    observacoes: Optional[str] = None

class SuggestionResponse(SuggestionBase):
    id: str  # Firebase usa strings como IDs
    status: SuggestionStatus
    usuario_id: str  # Firebase usa strings como IDs
    autor_nome: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    observacoes: Optional[str] = None
    
    class Config:
        from_attributes = True

class SuggestionList(BaseModel):
    suggestions: List[SuggestionResponse]
    total: int
    page: int
    per_page: int

# Report Models
class DashboardStats(BaseModel):
    total_suggestions: int
    total_users: int
    suggestions_this_month: int
    active_users: int
    pending_suggestions: int
    approved_suggestions: int

class SuggestionsByStatus(BaseModel):
    status: str
    count: int

class SuggestionsByMonth(BaseModel):
    month: str
    count: int

class UsersByDepartment(BaseModel):
    setor: str
    count: int

class DashboardData(BaseModel):
    stats: DashboardStats
    suggestions_by_status: List[SuggestionsByStatus]
    suggestions_by_month: List[SuggestionsByMonth]
    users_by_department: List[UsersByDepartment]

# System Models
class SystemHealth(BaseModel):
    status: str
    version: str
    database: str
    uptime: str
    message: str

class LogEntry(BaseModel):
    id: str  # Firebase usa strings como IDs
    user_id: Optional[str]  # Firebase usa strings como IDs
    action: str
    details: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class LogList(BaseModel):
    logs: List[LogEntry]
    total: int
    page: int
    per_page: int

# Configuration Models
class SystemConfig(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SyncConfig(BaseModel):
    google_sheets_enabled: bool
    google_sheets_url: Optional[str] = None
    sync_interval: str = "manual"
    auto_sync: bool = False

# Export Models
class ExportRequest(BaseModel):
    format: str  # "csv", "excel", "pdf"
    tables: List[str]
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filters: Optional[Dict[str, Any]] = None

# Update forward references
LoginResponse.model_rebuild()
UserProfile.model_rebuild()
