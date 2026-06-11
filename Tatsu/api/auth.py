"""
Tatsu AI — Authentication Module
=================================
Handles login, token generation, and JWT validation for cloud deployment.
"""

import jwt
import time
from fastapi import HTTPException, Security, Request, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import config

security = HTTPBearer(auto_error=False)

def create_token() -> str:
    """Create a new JWT token valid for 24 hours."""
    payload = {
        "sub": "admin",
        "exp": int(time.time()) + (24 * 3600)
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> bool:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub") == "admin"
    except jwt.PyJWTError:
        return False

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Dependency to check standard Authorization Header."""
    if config.DEPLOYMENT_MODE != "cloud":
        return True
        
    if not credentials or not verify_token(credentials.credentials):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

async def verify_websocket(websocket: WebSocket) -> bool:
    """Verify websocket token passed in query parameters."""
    if config.DEPLOYMENT_MODE != "cloud":
        return True
        
    token = websocket.query_params.get("token")
    if not token or not verify_token(token):
        return False
    return True
