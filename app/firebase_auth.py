"""
Firebase authentication helpers for protecting API endpoints.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import firebase_admin
from fastapi import Header, HTTPException, status
from firebase_admin import auth, credentials

from app.config import settings


@lru_cache(maxsize=1)
def _init_firebase() -> bool:
    """
    Initialize Firebase Admin SDK once.
    Returns True when initialized, False when disabled/misconfigured.
    """
    if firebase_admin._apps:
        return True

    # Preferred local/dev mode: explicit service-account JSON file.
    if settings.firebase_service_account_file:
        service_account = Path(settings.firebase_service_account_file)
        if service_account.exists():
            cred = credentials.Certificate(str(service_account))
            firebase_admin.initialize_app(cred)
            return True

    # Cloud Run / GCP mode: use application default credentials.
    try:
        firebase_admin.initialize_app()
        return True
    except Exception:
        return False


def verify_firebase_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """
    FastAPI dependency for Bearer token verification.
    If Firebase auth is disabled in .env, all requests are allowed (dev mode).
    """
    enabled = _init_firebase()
    if not enabled:
        return {"uid": "dev-user", "email": "dev@example.com", "auth_disabled": True}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token.",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {exc}",
        ) from exc
