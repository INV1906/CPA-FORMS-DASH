"""
Stubbed API endpoints that need Firebase implementation
These endpoints are currently using MySQL queries and need to be converted to Firebase
"""

from fastapi import HTTPException, status

def firebase_not_implemented():
    """Placeholder for endpoints not yet converted to Firebase"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This endpoint is being migrated to Firebase. Coming soon!"
    )

def firebase_feature_placeholder(feature_name: str):
    """Placeholder for specific Firebase features"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature_name} is being implemented with Firebase. Stay tuned!"
    )
