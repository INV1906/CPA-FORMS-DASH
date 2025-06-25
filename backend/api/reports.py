"""
Reports API endpoints - Firebase Firestore implementation
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from backend.models.schemas import DashboardData, DashboardStats, BaseResponse
from backend.api.auth import get_current_user
from backend.database.firebase_connection import firebase_manager
from collections import defaultdict

router = APIRouter()

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard statistics and charts data - Firebase implementation
    """
    try:
        # Get all suggestions
        suggestions_result = firebase_manager.query_collection("sugestoes")
        if not suggestions_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching suggestions")
        
        suggestions = suggestions_result.get('data', [])
        
        # Get all users
        users_result = firebase_manager.query_collection("usuarios")
        if not users_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching users")
        
        users = users_result.get('data', [])
        
        # Calculate basic stats
        total_suggestions = len(suggestions)
        
        # Count active users
        active_users = sum(1 for user in users if user.get('ativo', False))
        total_users = active_users
        
        # Count suggestions this month
        current_month = datetime.now().strftime('%Y-%m')
        suggestions_this_month = 0
        
        for suggestion in suggestions:
            created_at = suggestion.get('created_at')
            if created_at:
                # Handle both datetime objects and Firebase timestamps
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                if isinstance(created_at, datetime) and created_at.strftime('%Y-%m') == current_month:
                    suggestions_this_month += 1
        
        # Count suggestions by status
        status_counts = defaultdict(int)
        for suggestion in suggestions:
            status = suggestion.get('status', 'unknown')
            status_counts[status] += 1
        
        pending_suggestions = status_counts.get('pendente', 0)
        approved_suggestions = status_counts.get('aprovada', 0)
        
        dashboard_stats = DashboardStats(
            total_suggestions=total_suggestions,
            total_users=total_users,
            suggestions_this_month=suggestions_this_month,
            active_users=active_users,
            pending_suggestions=pending_suggestions,
            approved_suggestions=approved_suggestions
        )
        
        # Suggestions by status
        suggestions_by_status = [
            {"status": status, "count": count}
            for status, count in status_counts.items()
        ]
        
        # Suggestions by month (last 12 months)
        month_counts = defaultdict(int)
        cutoff_date = datetime.now() - timedelta(days=365)
        
        for suggestion in suggestions:
            created_at = suggestion.get('created_at')
            if created_at:
                # Handle both datetime objects and Firebase timestamps
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                if isinstance(created_at, datetime) and created_at >= cutoff_date:
                    month_key = created_at.strftime('%Y-%m')
                    month_counts[month_key] += 1
        
        suggestions_by_month = [
            {"month": month, "count": count}
            for month, count in sorted(month_counts.items())
        ]
        
        # Users by department
        dept_counts = defaultdict(int)
        for user in users:
            if user.get('ativo', False):
                setor = user.get('setor', 'Unknown')
                dept_counts[setor] += 1
        
        users_by_department = [
            {"setor": setor, "count": count}
            for setor, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return DashboardData(
            stats=dashboard_stats,
            suggestions_by_status=suggestions_by_status,
            suggestions_by_month=suggestions_by_month,
            users_by_department=users_by_department
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions-summary")
async def get_suggestions_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    setor: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get suggestions summary with filters - Firebase implementation
    """
    try:
        # Get all suggestions
        suggestions_result = firebase_manager.query_collection("sugestoes")
        if not suggestions_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching suggestions")
        
        suggestions = suggestions_result.get('data', [])
        
        # Apply filters
        filtered_suggestions = []
        
        for suggestion in suggestions:
            # Date filtering
            created_at = suggestion.get('created_at')
            if created_at:
                # Handle both datetime objects and Firebase timestamps
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                
                if date_from:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                    if created_at < date_from_obj:
                        continue
                
                if date_to:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                    if created_at > date_to_obj:
                        continue
            
            # Sector filtering
            if setor:
                setor_origem = suggestion.get('setor_origem', '')
                setor_destino = suggestion.get('setor_destino', '')
                if setor not in [setor_origem, setor_destino]:
                    continue
            
            # Non-admin users see only their department's data
            if current_user['tipo_usuario'] != 'admin':
                user_setor = current_user.get('setor', '')
                sugg_setor_origem = suggestion.get('setor_origem', '')
                sugg_setor_destino = suggestion.get('setor_destino', '')
                if user_setor not in [sugg_setor_origem, sugg_setor_destino]:
                    continue
            
            filtered_suggestions.append(suggestion)
        
        # Calculate summary statistics
        total_suggestions = len(filtered_suggestions)
        
        status_counts = defaultdict(int)
        priority_counts = defaultdict(int)
        setor_counts = defaultdict(int)
        
        for suggestion in filtered_suggestions:
            # Count by status
            status = suggestion.get('status', 'unknown')
            status_counts[status] += 1
            
            # Count by priority
            priority = suggestion.get('prioridade', 'unknown')
            priority_counts[priority] += 1
            
            # Count by origin sector
            setor_origem = suggestion.get('setor_origem', 'Unknown')
            setor_counts[setor_origem] += 1
        
        summary = {
            "total_suggestions": total_suggestions,
            "status_breakdown": dict(status_counts),
            "priority_breakdown": dict(priority_counts),
            "sector_breakdown": dict(setor_counts),
            "date_range": {
                "from": date_from,
                "to": date_to
            },
            "filters": {
                "setor": setor
            }        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-contributors")
async def get_top_contributors(
    limit: int = Query(10, ge=1, le=50),
    date_from: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get top contributors (users with most suggestions) - Firebase implementation
    """
    try:
        # Get all suggestions
        suggestions_result = firebase_manager.query_collection("sugestoes")
        if not suggestions_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching suggestions")
        
        suggestions = suggestions_result.get('data', [])
        
        # Get all users
        users_result = firebase_manager.query_collection("usuarios")
        if not users_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching users")
        
        users = users_result.get('data', [])
        user_map = {user.get('id'): user for user in users}
        
        # Apply date filter if provided
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            filtered_suggestions = []
            
            for suggestion in suggestions:
                created_at = suggestion.get('created_at')
                if created_at:
                    if hasattr(created_at, 'timestamp'):
                        created_at = datetime.fromtimestamp(created_at.timestamp())
                    if created_at >= date_from_obj:
                        filtered_suggestions.append(suggestion)
            suggestions = filtered_suggestions
        
        # Count suggestions per user
        user_counts = defaultdict(int)
        for suggestion in suggestions:
            user_id = suggestion.get('usuario_id')
            if user_id:
                user_counts[user_id] += 1
        
        # Build contributors list
        contributors = []
        for user_id, count in user_counts.items():
            user_data = user_map.get(user_id, {})
            contributors.append({
                "user_id": user_id,
                "nome": user_data.get('nome', 'Unknown'),
                "setor": user_data.get('setor', 'Unknown'), 
                "suggestions_count": count
            })
        
        # Sort by count and limit
        contributors.sort(key=lambda x: x['suggestions_count'], reverse=True)
        contributors = contributors[:limit]
        
        return {
            "contributors": contributors,
            "total_contributors": len(user_counts),
            "date_from": date_from,
            "limit": limit
        }        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-activity")
async def get_user_activity(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user activity statistics - Firebase implementation
    """
    try:
        date_from = datetime.now() - timedelta(days=days)
        
        # Get all users
        users_result = firebase_manager.query_collection("usuarios")
        if not users_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching users")
        
        users = users_result.get('data', [])
        
        # Get all suggestions
        suggestions_result = firebase_manager.query_collection("sugestoes")
        if not suggestions_result['success']:
            raise HTTPException(status_code=500, detail="Error fetching suggestions")
        
        suggestions = suggestions_result.get('data', [])
        
        # Calculate user registration activity
        registration_activity = defaultdict(int)
        for user in users:
            created_at = user.get('created_at')
            if created_at:
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                if created_at >= date_from:
                    date_key = created_at.strftime('%Y-%m-%d')
                    registration_activity[date_key] += 1
        
        # Calculate suggestion creation activity
        suggestion_activity = defaultdict(int)
        for suggestion in suggestions:
            created_at = suggestion.get('created_at')
            if created_at:
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                if created_at >= date_from:
                    date_key = created_at.strftime('%Y-%m-%d')
                    suggestion_activity[date_key] += 1
        
        # Calculate department activity
        dept_suggestions = defaultdict(int)
        dept_users = defaultdict(set)
        
        # Count suggestions by department origin
        for suggestion in suggestions:
            created_at = suggestion.get('created_at')
            if created_at:
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                if created_at >= date_from:
                    setor = suggestion.get('setor_origem', 'Unknown')
                    dept_suggestions[setor] += 1
                    user_id = suggestion.get('usuario_id')
                    if user_id:
                        dept_users[setor].add(user_id)
        
        # Build department activity list
        department_activity = []
        for setor, suggestion_count in dept_suggestions.items():
            department_activity.append({
                "setor": setor,
                "suggestions_count": suggestion_count,
                "active_users": len(dept_users[setor])
            })
        
        department_activity.sort(key=lambda x: x['suggestions_count'], reverse=True)
        
        return {
            "period_days": days,
            "registration_activity": [
                {"date": date, "new_users": count}
                for date, count in sorted(registration_activity.items())
            ],
            "suggestion_activity": [
                {"date": date, "new_suggestions": count}
                for date, count in sorted(suggestion_activity.items())
            ],
            "department_activity": department_activity
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export-data")
async def export_data(
    format: str = Query("json", regex="^(json)$"),
    table: str = Query("sugestoes", regex="^(sugestoes|usuarios)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Export data in JSON format - Firebase implementation
    Note: Only JSON export is supported with Firebase
    """
    # Check permissions for sensitive data
    if table == "usuarios" and current_user['tipo_usuario'] != 'admin':
        raise HTTPException(
            status_code=403,
            detail="Admin access required for user data export"
        )
    
    try:
        # Get data from Firebase
        result = firebase_manager.query_collection(table)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail="Database error")
        
        data = result.get('data', [])
        
        # Filter for non-admin users on suggestions
        if current_user['tipo_usuario'] != 'admin' and table == "sugestoes":
            data = [s for s in data if s.get('usuario_id') == current_user['id']]
        
        # Convert Firebase timestamps to ISO strings for JSON serialization
        for item in data:
            for key, value in item.items():
                if hasattr(value, 'timestamp'):
                    item[key] = datetime.fromtimestamp(value.timestamp()).isoformat()
        
        return {
            "table": table,
            "count": len(data),
            "data": data,
            "exported_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
