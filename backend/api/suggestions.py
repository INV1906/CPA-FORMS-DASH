"""
Suggestions API endpoints - Firebase Firestore implementation
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from backend.models.schemas import (
    SuggestionCreate, SuggestionUpdate, SuggestionResponse, 
    SuggestionList, BaseResponse
)
from backend.api.auth import get_current_user, get_admin_user
from backend.services.auth_service import auth_service
from backend.database.firebase_connection import firebase_manager
from datetime import datetime
import uuid

router = APIRouter()

@router.get("/", response_model=SuggestionList)
async def list_suggestions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    setor: Optional[str] = Query(None),
    autor: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    List suggestions with filters - Firebase implementation
    """
    try:
        # Build Firebase query filters
        filters = []
        
        # Non-admin users can only see their own suggestions
        if current_user['tipo_usuario'] != 'admin':
            filters.append(("usuario_id", "==", current_user['id']))
        
        if status:
            filters.append(("status", "==", status))
        
        if setor:
            # For sector filtering, we'll need to check both origem and destino
            # This is a limitation in Firestore - we can't do OR queries easily
            # For now, we'll filter by setor_origem
            filters.append(("setor_origem", "==", setor))
        
        # Get all suggestions with filters
        result = firebase_manager.query_collection("sugestoes", filters=filters, order_by="created_at")
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Database error")
        
        suggestions_data = result.get('data', [])
          # Additional filtering for autor (name search) - done in memory since Firestore doesn't support LIKE
        if autor:
            filtered_suggestions = []
            for suggestion in suggestions_data:
                # Get user data to check name
                user_result = firebase_manager.get_document("usuarios", suggestion.get('usuario_id', ''))
                if user_result['success'] and user_result.get('data'):
                    user_data = user_result['data']
                    if autor.lower() in user_data.get('nome', '').lower():
                        suggestion['autor_nome'] = user_data.get('nome', 'Unknown')
                        filtered_suggestions.append(suggestion)
            suggestions_data = filtered_suggestions
        else:
            # Add author names to all suggestions
            for suggestion in suggestions_data:
                user_result = firebase_manager.get_document("usuarios", suggestion.get('usuario_id', ''))
                if user_result['success'] and user_result.get('data'):
                    suggestion['autor_nome'] = user_result['data'].get('nome', 'Unknown')
                else:
                    suggestion['autor_nome'] = 'Unknown'
        
        # Manual pagination since Firestore pagination is more complex
        total = len(suggestions_data)
        offset = (page - 1) * per_page
        paginated_suggestions = suggestions_data[offset:offset + per_page]
        
        # Convert to response models
        suggestions = []
        for suggestion_data in paginated_suggestions:
            # Convert Firebase timestamp to datetime if needed
            if 'created_at' in suggestion_data and hasattr(suggestion_data['created_at'], 'timestamp'):
                suggestion_data['created_at'] = datetime.fromtimestamp(suggestion_data['created_at'].timestamp())
            if 'updated_at' in suggestion_data and hasattr(suggestion_data['updated_at'], 'timestamp'):
                suggestion_data['updated_at'] = datetime.fromtimestamp(suggestion_data['updated_at'].timestamp())
            
            # Ensure we have all required fields with defaults
            suggestion_data.setdefault('observacoes', None)
            suggestion_data.setdefault('updated_at', None)
            
            suggestions.append(SuggestionResponse(**suggestion_data))
        
        return SuggestionList(
            suggestions=suggestions,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=SuggestionResponse)
async def create_suggestion(
    suggestion_data: SuggestionCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create new suggestion - Firebase implementation
    """
    try:
        # Prepare suggestion data
        suggestion_doc = {
            "titulo": suggestion_data.titulo,
            "descricao": suggestion_data.descricao,
            "setor_origem": suggestion_data.setor_origem,
            "setor_destino": suggestion_data.setor_destino,
            "prioridade": suggestion_data.prioridade,
            "status": "pendente",  # Default status
            "usuario_id": current_user['id'],
            "observacoes": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Create suggestion in Firebase
        result = firebase_manager.create_document("sugestoes", suggestion_doc)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Failed to create suggestion")
        
        # Get the created suggestion with author name
        suggestion_id = result['id']
        suggestion_doc['id'] = suggestion_id
        
        # Get author name
        user_result = firebase_manager.get_document("usuarios", current_user['id'])
        if user_result['success'] and user_result.get('data'):
            suggestion_doc['autor_nome'] = user_result['data'].get('nome', 'Unknown')
        else:
            suggestion_doc['autor_nome'] = 'Unknown'
        
        # Log action
        auth_service.log_user_action(
            current_user['id'],
            "CREATE_SUGGESTION",
            f"Created suggestion: {suggestion_data.titulo}"
        )
        
        return SuggestionResponse(**suggestion_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get suggestion by ID - Firebase implementation
    """
    try:
        # Get suggestion from Firebase
        result = firebase_manager.get_document("sugestoes", suggestion_id)
        
        if not result['success'] or not result.get('data'):
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        suggestion = result['data']
        
        # Check permission (users can only see their own suggestions unless admin)
        if (current_user['tipo_usuario'] != 'admin' and 
            suggestion.get('usuario_id') != current_user['id']):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this suggestion"
            )
        
        # Get author name
        user_result = firebase_manager.get_document("usuarios", suggestion.get('usuario_id', ''))
        if user_result['success'] and user_result.get('data'):
            suggestion['autor_nome'] = user_result['data'].get('nome', 'Unknown')
        else:
            suggestion['autor_nome'] = 'Unknown'
        
        # Convert Firebase timestamp to datetime if needed
        if 'created_at' in suggestion and hasattr(suggestion['created_at'], 'timestamp'):
            suggestion['created_at'] = datetime.fromtimestamp(suggestion['created_at'].timestamp())
        if 'updated_at' in suggestion and hasattr(suggestion['updated_at'], 'timestamp'):
            suggestion['updated_at'] = datetime.fromtimestamp(suggestion['updated_at'].timestamp())
        
        # Ensure required fields
        suggestion.setdefault('observacoes', None)
        suggestion.setdefault('updated_at', None)
        
        return SuggestionResponse(**suggestion)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion(
    suggestion_id: str,
    suggestion_data: SuggestionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update suggestion - Firebase implementation
    """
    try:
        # Get current suggestion
        current_result = firebase_manager.get_document("sugestoes", suggestion_id)
        
        if not current_result['success'] or not current_result.get('data'):
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        current_suggestion = current_result['data']
        
        # Check permission
        is_author = current_suggestion.get('usuario_id') == current_user['id']
        is_admin = current_user['tipo_usuario'] == 'admin'
        
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to update this suggestion"
            )
        
        # Authors can only edit their own pending suggestions
        if is_author and not is_admin and current_suggestion.get('status') != 'pendente':
            raise HTTPException(
                status_code=403,
                detail="Can only edit pending suggestions"
            )
        
        # Build update data
        update_data = {}
        
        if suggestion_data.titulo is not None:
            update_data['titulo'] = suggestion_data.titulo
        
        if suggestion_data.descricao is not None:
            update_data['descricao'] = suggestion_data.descricao
        
        if suggestion_data.setor_destino is not None:
            update_data['setor_destino'] = suggestion_data.setor_destino
        
        if suggestion_data.prioridade is not None:
            update_data['prioridade'] = suggestion_data.prioridade
        
        # Only admin can change status and add observations
        if is_admin:
            if suggestion_data.status is not None:
                update_data['status'] = suggestion_data.status
            
            if suggestion_data.observacoes is not None:
                update_data['observacoes'] = suggestion_data.observacoes
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        # Update timestamp
        update_data['updated_at'] = datetime.now()
        
        # Update in Firebase
        result = firebase_manager.update_document("sugestoes", suggestion_id, update_data)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Failed to update suggestion")
        
        # Get updated suggestion
        updated_result = firebase_manager.get_document("sugestoes", suggestion_id)
        if not updated_result['success'] or not updated_result.get('data'):
            raise HTTPException(status_code=500, detail="Failed to retrieve updated suggestion")
        
        updated_suggestion = updated_result['data']
        
        # Get author name
        user_result = firebase_manager.get_document("usuarios", updated_suggestion.get('usuario_id', ''))
        if user_result['success'] and user_result.get('data'):
            updated_suggestion['autor_nome'] = user_result['data'].get('nome', 'Unknown')
        else:
            updated_suggestion['autor_nome'] = 'Unknown'
        
        # Convert Firebase timestamp to datetime if needed
        if 'created_at' in updated_suggestion and hasattr(updated_suggestion['created_at'], 'timestamp'):
            updated_suggestion['created_at'] = datetime.fromtimestamp(updated_suggestion['created_at'].timestamp())
        if 'updated_at' in updated_suggestion and hasattr(updated_suggestion['updated_at'], 'timestamp'):
            updated_suggestion['updated_at'] = datetime.fromtimestamp(updated_suggestion['updated_at'].timestamp())
        
        # Ensure required fields
        updated_suggestion.setdefault('observacoes', None)
        updated_suggestion.setdefault('updated_at', None)
        
        # Log action
        auth_service.log_user_action(
            current_user['id'],
            "UPDATE_SUGGESTION",
            f"Updated suggestion: {updated_suggestion.get('titulo', suggestion_id)}"
        )
        
        return SuggestionResponse(**updated_suggestion)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = %s")
        params.append(datetime.now())
        params.append(suggestion_id)
        
        # Update suggestion
        update_query = f"UPDATE sugestoes SET {', '.join(updates)} WHERE id = %s"
        result = db_manager.execute_query(update_query, params)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Failed to update suggestion")
        
        # Get updated suggestion
        get_updated_query = """
        SELECT 
            s.id, s.titulo, s.descricao, s.status, s.prioridade,
            s.setor_origem, s.setor_destino, s.usuario_id,
            s.created_at, s.updated_at, s.observacoes,
            u.nome as autor_nome
        FROM sugestoes s
        LEFT JOIN usuarios u ON s.usuario_id = u.id
        WHERE s.id = %s
        """
        
        suggestion_result = db_manager.execute_query(get_updated_query, (suggestion_id,))
        
        if not suggestion_result['success'] or not suggestion_result['data']:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated suggestion")
        
        # Log action
        auth_service.log_user_action(
            current_user['id'],
            "UPDATE_SUGGESTION",
            f"Updated suggestion ID: {suggestion_id}"
        )
        
        return SuggestionResponse(**suggestion_result['data'][0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{suggestion_id}", response_model=BaseResponse)
async def delete_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete suggestion - Firebase implementation
    """
    try:
        # Get current suggestion
        result = firebase_manager.get_document("sugestoes", suggestion_id)
        
        if not result['success'] or not result.get('data'):
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        suggestion = result['data']
        
        # Check permission
        is_author = suggestion.get('usuario_id') == current_user['id']
        is_admin = current_user['tipo_usuario'] == 'admin'
        
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to delete this suggestion"
            )
          # Delete suggestion from Firebase
        delete_result = firebase_manager.delete_document("sugestoes", suggestion_id)
        
        if not delete_result['success']:
            raise HTTPException(status_code=500, detail="Failed to delete suggestion")
          # Log action
        auth_service.log_user_action(
            current_user['id'],
            "DELETE_SUGGESTION",
            f"Deleted suggestion: {suggestion.get('titulo', 'Unknown')} (ID: {suggestion_id})"
        )
        
        return BaseResponse(
            success=True,
            message="Suggestion deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
