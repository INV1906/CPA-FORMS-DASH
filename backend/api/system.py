"""
System API endpoints - Firebase Firestore implementation
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from backend.models.schemas import SystemHealth, LogList, LogEntry, BaseResponse
from backend.api.auth import get_current_user, get_admin_user
from backend.services.auth_service import auth_service
from backend.database.firebase_connection import firebase_manager
from collections import defaultdict

router = APIRouter()

@router.get("/health", response_model=SystemHealth)
async def health_check():
    """
    System health check - Firebase implementation
    """
    try:
        # Test Firebase connection
        db_status = "ok" if firebase_manager.is_connected() else "error"
        
        # Calculate uptime (simplified)
        uptime = "Running"
        
        # Additional Firebase status info
        status_message = "Sistema de Gestão de Sugestões API"
        if firebase_manager.is_demo_mode:
            status_message += " (Demo Mode - Firebase)"
        else:
            status_message += " (Firebase Firestore)"
        
        return SystemHealth(
            status="ok" if db_status == "ok" else "error",
            version="2.0.0",
            database=f"Firebase Firestore ({('Demo' if firebase_manager.is_demo_mode else 'Connected')})",
            uptime=uptime,
            message=status_message
        )
        
    except Exception as e:
        return SystemHealth(
            status="error",
            version="2.0.0",
            database="error",
            uptime="Unknown",
            message=f"System error: {str(e)}"
        )

@router.get("/logs", response_model=LogList)
async def get_system_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get system logs (admin only) - Firebase implementation
    """
    try:
        # Get all logs from Firebase
        logs_result = firebase_manager.query_collection("logs", order_by="created_at")
        
        if not logs_result['success']:
            raise HTTPException(status_code=500, detail="Database error")
        
        logs_data = logs_result.get('data', [])
        
        # Apply filters
        filtered_logs = []
        
        for log in logs_data:
            # Action filter
            if action and action.lower() not in log.get('action', '').lower():
                continue
            
            # User ID filter
            if user_id and log.get('user_id') != user_id:
                continue
            
            # Date filters
            created_at = log.get('created_at')
            if created_at:
                # Handle both datetime objects and Firebase timestamps
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                
                if date_from:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                    if created_at < date_from_obj:
                        continue
                
                if date_to:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                    if created_at >= date_to_obj:
                        continue
            
            filtered_logs.append(log)
        
        # Sort by created_at descending
        filtered_logs.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        # Manual pagination
        total = len(filtered_logs)
        offset = (page - 1) * per_page
        paginated_logs = filtered_logs[offset:offset + per_page]
        
        # Convert to response models
        logs = []
        for log_data in paginated_logs:
            # Convert Firebase timestamp to datetime if needed
            if 'created_at' in log_data and hasattr(log_data['created_at'], 'timestamp'):
                log_data['created_at'] = datetime.fromtimestamp(log_data['created_at'].timestamp())
              # Ensure required fields with defaults
            log_data.setdefault('user_id', None)
            log_data.setdefault('ip_address', None)
            log_data.setdefault('user_agent', None)
            
            logs.append(LogEntry(**log_data))
        
        return LogList(
            logs=logs,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_system_stats(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get detailed system statistics (admin only) - Firebase implementation
    """
    try:
        # Get basic Firebase collection stats
        collections_stats = []
        
        # Check suggestions collection
        suggestions_result = firebase_manager.query_collection("sugestoes")
        suggestions_count = len(suggestions_result.get('data', [])) if suggestions_result['success'] else 0
        collections_stats.append({"collection": "sugestoes", "count": suggestions_count})
        
        # Check users collection
        users_result = firebase_manager.query_collection("usuarios")
        users_count = len(users_result.get('data', [])) if users_result['success'] else 0
        collections_stats.append({"collection": "usuarios", "count": users_count})
        
        # Check logs collection
        logs_result = firebase_manager.query_collection("logs")
        logs_count = len(logs_result.get('data', [])) if logs_result['success'] else 0
        collections_stats.append({"collection": "logs", "count": logs_count})
        
        return {
            "database_stats": collections_stats,
            "database_type": "Firebase Firestore",
            "demo_mode": firebase_manager.is_demo_mode,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backup", response_model=BaseResponse)
async def create_backup(
    current_user: dict = Depends(get_admin_user)
):
    """
    Create database backup (admin only) - Firebase note
    """
    try:
        # Log the backup action
        auth_service.log_user_action(
            current_user['id'],
            "BACKUP_REQUESTED",
            "Manual backup requested for Firebase data"
        )
        
        return BaseResponse(
            success=True,
            message="Firebase Firestore has automatic backups. Manual exports can be done through Firebase Console."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_system_config(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get system configuration (admin only) - Firebase implementation
    """
    try:
        # Get configuration from Firebase
        config_result = firebase_manager.query_collection("configuracoes")
        
        if not config_result['success']:
            # Return default config
            return {
                "sistema_nome": "Sistema de Gestão de Sugestões",
                "version": "2.0.0",
                "environment": "Firebase",
                "maintenance_mode": False,
                "demo_mode": firebase_manager.is_demo_mode
            }
        
        # Convert to dictionary
        config = {
            "sistema_nome": "Sistema de Gestão de Sugestões",
            "version": "2.0.0",
            "environment": "Firebase",
            "maintenance_mode": False,
            "demo_mode": firebase_manager.is_demo_mode
        }
        
        for row in config_result.get('data', []):
            config[row.get('chave', 'unknown')] = row.get('valor', '')
        
        return config
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/config", response_model=BaseResponse)
async def update_system_config(
    config_data: dict,
    current_user: dict = Depends(get_admin_user)
):
    """
    Update system configuration (admin only) - Firebase implementation
    """
    try:
        updated_count = 0
        
        for key, value in config_data.items():
            # Skip read-only config
            if key in ['version', 'environment', 'demo_mode']:
                continue
                
            # Create or update configuration document
            config_doc = {
                "chave": key,
                "valor": str(value),
                "tipo": "texto",
                "categoria": "geral",
                "updated_at": datetime.now()
            }
            
            result = firebase_manager.create_document("configuracoes", config_doc)
            if result['success']:
                updated_count += 1
        
        # Log the configuration change
        auth_service.log_user_action(
            current_user['id'],
            "CONFIG_UPDATED",
            f"Updated {updated_count} configuration items"
        )
        
        return BaseResponse(
            success=True,
            message=f"Updated {updated_count} configuration items"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/logs/cleanup", response_model=BaseResponse)
async def cleanup_old_logs(
    days: int = Query(90, ge=1, le=365),
    current_user: dict = Depends(get_admin_user)
):
    """
    Delete logs older than specified days (admin only) - Firebase implementation
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all logs
        logs_result = firebase_manager.query_collection("logs")
        if not logs_result['success']:
            return BaseResponse(success=True, message="No logs found")
        
        logs_data = logs_result.get('data', [])
        logs_to_delete = []
        
        # Find logs older than cutoff date
        for log in logs_data:
            created_at = log.get('created_at')
            if created_at:
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                if created_at < cutoff_date:
                    logs_to_delete.append(log.get('id'))
        
        if not logs_to_delete:
            return BaseResponse(
                success=True,
                message="No old logs found to delete"
            )
        
        # Delete old logs
        deleted_count = 0
        for log_id in logs_to_delete:
            result = firebase_manager.delete_document("logs", log_id)
            if result['success']:
                deleted_count += 1
        
        # Log the cleanup action
        auth_service.log_user_action(
            current_user['id'],
            "LOGS_CLEANUP",
            f"Deleted {deleted_count} logs older than {days} days"
        )
        
        return BaseResponse(
            success=True,
            message=f"Deleted {deleted_count} old logs"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
