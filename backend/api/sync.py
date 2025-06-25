"""
API endpoints para sincronização Google Forms
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any
from datetime import datetime

from backend.services.google_forms_sync import google_forms_sync
from backend.api.auth import get_current_user, require_admin
from backend.models.schemas import BaseResponse

router = APIRouter(prefix="/sync", tags=["Sincronização Google Forms"])

@router.post("/google-forms/manual", response_model=BaseResponse)
async def sync_google_forms_manual(
    current_user: dict = Depends(require_admin)
):
    """
    Executar sincronização manual do Google Forms
    Requer privilégios de admin
    """
    try:
        result = google_forms_sync.sync_now()
        
        return BaseResponse(
            success=result["success"],
            message=result["message"],
            data={
                "imported": result.get("imported", 0),
                "total_found": result.get("total_found", 0),
                "sync_time": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na sincronização: {str(e)}"
        )

@router.get("/google-forms/status", response_model=BaseResponse)
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    """
    Obter status da sincronização Google Forms
    """
    try:
        from backend.core.config import settings
        from pathlib import Path
        
        last_sync_file = Path(settings.LAST_SYNC_TIMESTAMP_FILE)
        last_sync = None
        
        if last_sync_file.exists():
            try:
                with open(last_sync_file, 'r') as f:
                    last_sync = f.read().strip()
            except:
                pass
        
        status_data = {
            "auto_sync_enabled": settings.AUTO_SYNC_ENABLED,
            "sync_interval": settings.SYNC_INTERVAL,
            "google_sheets_id": settings.GOOGLE_SHEETS_ID[:10] + "..." if settings.GOOGLE_SHEETS_ID else "Não configurado",
            "last_sync": last_sync,
            "credentials_configured": bool(settings.GOOGLE_CREDENTIALS_FILE and Path(settings.GOOGLE_CREDENTIALS_FILE).exists()),
            "google_api_available": google_forms_sync.sheets_service is not None
        }
        
        return BaseResponse(
            success=True,
            message="Status da sincronização obtido",
            data=status_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter status: {str(e)}"
        )

@router.post("/google-forms/test", response_model=BaseResponse)
async def test_google_forms_connection(
    current_user: dict = Depends(require_admin)
):
    """
    Testar conexão com Google Forms/Sheets
    """
    try:
        if not google_forms_sync.sheets_service:
            return BaseResponse(
                success=False,
                message="Google Sheets não configurado",
                data={"error": "Serviço não inicializado"}
            )
        
        # Testar busca de dados
        responses = google_forms_sync.fetch_new_responses()
        
        return BaseResponse(
            success=True,
            message="Conexão testada com sucesso",
            data={
                "connected": True,
                "test_result": f"Encontradas {len(responses)} respostas para sincronizar",
                "sheets_id": google_forms_sync.credentials is not None
            }
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            message=f"Erro no teste de conexão: {str(e)}",
            data={"error": str(e)}
        )

@router.post("/google-forms/configure", response_model=BaseResponse)
async def configure_google_forms_sync(
    config_data: Dict[str, Any],
    current_user: dict = Depends(require_admin)
):
    """
    Configurar sincronização Google Forms
    """
    try:
        # Validar dados de configuração
        required_fields = ["google_sheets_id"]
        for field in required_fields:
            if field not in config_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campo obrigatório: {field}"
                )
        
        # Atualizar configurações (você pode salvar no Firebase ou arquivo)
        from backend.database.firebase_connection import firebase_manager
        
        config_updates = {
            "google_sheets_id": config_data["google_sheets_id"],
            "auto_sync_enabled": config_data.get("auto_sync_enabled", True),
            "sync_interval": config_data.get("sync_interval", 30),
            "updated_at": datetime.now(),
            "updated_by": current_user["id"]
        }
        
        # Salvar configuração no Firebase
        result = firebase_manager.create_document("configuracoes_sync", config_updates)
        
        if result["success"]:
            return BaseResponse(
                success=True,
                message="Configuração atualizada com sucesso",
                data=config_updates
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Erro ao salvar configuração"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na configuração: {str(e)}"
        )

@router.get("/google-forms/preview", response_model=BaseResponse)
async def preview_google_forms_data(
    current_user: dict = Depends(require_admin)
):
    """
    Visualizar dados que seriam importados (sem salvar)
    """
    try:
        responses = google_forms_sync.fetch_new_responses()
        
        if not responses:
            return BaseResponse(
                success=True,
                message="Nenhuma nova resposta para importar",
                data={"responses": []}
            )
        
        # Mapear apenas os primeiros 5 para preview
        preview_data = []
        for response in responses[:5]:
            mapped = google_forms_sync._map_form_to_suggestion(response)
            preview_data.append({
                "raw_form_data": response["raw_data"],
                "mapped_suggestion": mapped
            })
        
        return BaseResponse(
            success=True,
            message=f"Preview de {len(responses)} resposta(s)",
            data={
                "total_new_responses": len(responses),
                "preview": preview_data,
                "would_import": len(responses)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro no preview: {str(e)}"
        )
