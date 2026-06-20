from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name=settings.api_key_name, auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    if settings.debug and not api_key:
        return "dev-user"
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key
