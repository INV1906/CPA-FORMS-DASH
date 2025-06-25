"""
Backend API - Sistema de Gestão de Sugestões
FastAPI application with JWT authentication and MySQL database
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

# Import modules
from backend.database.firebase_connection import firebase_manager
from backend.api import auth, users, suggestions, reports, system, sync
from backend.core.config import settings

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Sistema de Gestão de Sugestões API")
    print(f"📊 Database: {settings.DATABASE_HOST}")
    print(f"🔧 Environment: {settings.ENVIRONMENT}")    
    
    # Test database connection
    if settings.FIREBASE_ENABLED:
        print("🔥 Using Firebase Firestore")
        if firebase_manager.is_connected():
            print("✅ Firebase connection successful")
        else:
            print("❌ Firebase connection failed")
    else:
        print("⚠️ MySQL not supported in this version")
        print("🔥 Using Firebase Firestore")
        if firebase_manager.is_connected():
            print("✅ Firebase connection successful")
        else:
            print("❌ Firebase connection failed")
    
    # Initialize Google Forms sync
    if settings.AUTO_SYNC_ENABLED:
        print("🔄 Inicializando sincronização Google Forms...")
        try:
            from backend.services.google_forms_sync import google_forms_sync
            import asyncio
            # Iniciar sincronização em background
            asyncio.create_task(google_forms_sync.start_background_sync())
            print("✅ Sincronização automática iniciada")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar sincronização: {e}")
    else:
        print("ℹ️ Sincronização automática desabilitada")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down API")

# Create FastAPI app
app = FastAPI(
    title="Sistema de Gestão de Sugestões",
    description="""
    API REST para gerenciamento de sugestões acadêmicas com autenticação JWT,
    controle de acesso por setores e integração com Google Sheets.
    
    ## Recursos Principais
    
    * **Autenticação JWT** - Login seguro com tokens
    * **Gestão de Usuários** - CRUD completo com controle de acesso
    * **Gestão de Sugestões** - Criação, edição e workflow
    * **Relatórios e Analytics** - Dashboards e métricas
    * **Integração Google Sheets** - Sincronização automática
    * **Logs de Auditoria** - Rastreamento completo
    
    ## Autenticação
    
    Use o endpoint `/auth/login` para obter um token JWT e incluir o header:
    ```
    Authorization: Bearer <seu_token_jwt>
    ```
    """,
    version="2.0.0",
    contact={
        "name": "Equipe Projeto Integrador",
        "email": "admin@sistema.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")

# API Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(sync.router, prefix="/api", tags=["Sincronização"])

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main frontend page"""
    frontend_file = frontend_dir / "index.html"
    if frontend_file.exists():
        return FileResponse(frontend_file)
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sistema de Gestão de Sugestões</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0; padding: 0; min-height: 100vh;
                display: flex; align-items: center; justify-content: center;
            }
            .container {
                background: white; border-radius: 20px; padding: 40px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center; max-width: 600px;
            }
            h1 { color: #333; margin-bottom: 20px; }
            .status { background: #e8f5e8; color: #4caf50; padding: 15px; 
                     border-radius: 10px; margin: 20px 0; }
            .links { margin-top: 30px; }
            .link { display: inline-block; margin: 10px; padding: 12px 24px;
                   background: #667eea; color: white; text-decoration: none;
                   border-radius: 8px; transition: all 0.3s; }
            .link:hover { background: #5a6fd8; transform: translateY(-2px); }
            .api-info { background: #f5f5f5; padding: 20px; border-radius: 10px;
                       margin-top: 20px; text-align: left; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎓 Sistema de Gestão de Sugestões</h1>
            <div class="status">
                ✅ <strong>API Backend Funcionando</strong><br>
                FastAPI + MySQL + JWT Authentication
            </div>
            
            <p>Backend API pronto para integração com interface personalizada do Figma!</p>
            
            <div class="links">
                <a href="/docs" class="link">📚 Documentação da API</a>
                <a href="/redoc" class="link">📖 ReDoc</a>
                <a href="/api/system/health" class="link">🔍 Health Check</a>
            </div>
            
            <div class="api-info">
                <h3>🔧 Informações da API</h3>
                <p><strong>Base URL:</strong> <code>http://localhost:8000/api</code></p>
                <p><strong>Login:</strong> <code>POST /api/auth/login</code></p>
                <p><strong>Usuário Admin:</strong> admin@sistema.com / admin123</p>
                <p><strong>Recursos:</strong> Users, Suggestions, Reports, System</p>
            </div>
        </div>
    </body>
    </html>
    """)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Firebase database
        db_status = "ok" if firebase_manager.is_connected() else "error"
    except Exception:
        db_status = "error"
    
    return {
        "status": "ok",
        "version": "2.0.0",
        "database": db_status,
        "message": "Sistema de Gestão de Sugestões API"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
