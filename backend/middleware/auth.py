from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from backend.config import AUTH0_AUDIENCE, AUTH0_DOMAIN, AUTH_DISABLED

security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _jwks() -> dict[str, Any]:
    if not AUTH0_DOMAIN:
        return {"keys": []}
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    with httpx.Client(timeout=10.0) as client:
        return client.get(url).json()



def require_m2m_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if AUTH_DISABLED:
        return {"sub": "dev"}

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = credentials.credentials
    try:
        unverified = jwt.get_unverified_header(token)
        key = next((k for k in _jwks().get("keys", []) if k.get("kid") == unverified.get("kid")), None)
        if not key:
            raise HTTPException(status_code=401, detail="Signing key not found")

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
        return claims
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
