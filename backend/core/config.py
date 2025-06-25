"""
Configuration settings for the application
Uses environment variables with fallback defaults
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class Settings:
    """Application settings"""
    
    # App Info
    APP_NAME: str = "Sistema de Gestão de Sugestões"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_PREFIX: str = "/api"
    
    # Database
    DATABASE_HOST: str = os.getenv("DB_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DATABASE_USER: str = os.getenv("DB_USER", "root")
    DATABASE_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DATABASE_NAME: str = os.getenv("DB_NAME", "projeto_integrador")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
      # External Services
    GOOGLE_SHEETS_ENABLED: bool = os.getenv("AUTO_SYNC_ENABLED", "False").lower() == "true"
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "config/google-credentials.json")
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_FORMS_ID: str = os.getenv("GOOGLE_FORMS_ID", "")
    GOOGLE_SHEETS_NAME: str = os.getenv("GOOGLE_SHEETS_NAME", "forms")
    GOOGLE_SHEETS_SCOPES: list = os.getenv("GOOGLE_SHEETS_SCOPES", "").split(",")
      # Sync Configuration
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "30"))
    AUTO_SYNC_ENABLED: bool = os.getenv("AUTO_SYNC_ENABLED", "False").lower() == "true"
    WEBHOOK_ENABLED: bool = os.getenv("WEBHOOK_ENABLED", "False").lower() == "true"
    LAST_SYNC_TIMESTAMP_FILE: str = os.getenv("LAST_SYNC_TIMESTAMP_FILE", "data/last_sync.txt")    # Firebase Configuration
    FIREBASE_ENABLED: bool = os.getenv("FIREBASE_ENABLED", "True").lower() == "true"
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "projeto-integrador-sugestoes")
    FIREBASE_PRIVATE_KEY_ID: str = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")
    FIREBASE_PRIVATE_KEY: str = os.getenv("FIREBASE_PRIVATE_KEY", "")
    FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")
    FIREBASE_CLIENT_ID: str = os.getenv("FIREBASE_CLIENT_ID", "")
    FIREBASE_AUTH_URI: str = os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
    FIREBASE_TOKEN_URI: str = os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token")
    
    # Email
    EMAIL_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Frontend
    FRONTEND_DIR: str = "frontend"
    STATIC_DIR: str = "frontend/static"

    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database connection URL"""
        return (
            f"mysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

# Create settings instance
settings = Settings()

# Ensure directories exist
try:
    Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
    Path(settings.FRONTEND_DIR).mkdir(exist_ok=True)
    Path(settings.STATIC_DIR).mkdir(exist_ok=True)
except Exception:
    pass  # Ignore errors during directory creation
