"""
Optional Firestore sync helpers.

When Firebase service account is configured, email records are mirrored to Firestore.
If not configured, all methods become safe no-ops.
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import settings

COLLECTION_NAME = "email_records"


@lru_cache(maxsize=1)
def _firestore_client():
    if not firebase_admin._apps:
        service_account_path = settings.firebase_service_account_file
        if service_account_path:
            service_account = Path(service_account_path)
            if service_account.exists():
                cred = credentials.Certificate(str(service_account))
                firebase_admin.initialize_app(cred)
            else:
                return None
        else:
            # Cloud Run / GCP mode: use application default credentials.
            try:
                firebase_admin.initialize_app()
            except Exception:
                return None
    return firestore.client()


def firestore_enabled() -> bool:
    return _firestore_client() is not None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sync_email_record(record: dict) -> None:
    """Mirror newly processed email record into Firestore."""
    client = _firestore_client()
    if client is None:
        return
    doc_id = record["gmail_message_id"]
    payload = {**record, "synced_at": _now_iso()}
    client.collection(COLLECTION_NAME).document(doc_id).set(payload, merge=True)


def sync_approval_status(gmail_message_id: str, status: str, edited_reply: Optional[str] = None) -> None:
    """Mirror approval status updates into Firestore."""
    client = _firestore_client()
    if client is None:
        return
    payload = {"approval_status": status, "synced_at": _now_iso()}
    if edited_reply is not None:
        payload["generated_reply"] = edited_reply
    client.collection(COLLECTION_NAME).document(gmail_message_id).set(payload, merge=True)


def list_firestore_emails(status: Optional[str] = None, limit: int = 100) -> list[dict]:
    """
    Read email records from Firestore.
    Returns empty list if Firestore is not configured.
    """
    client = _firestore_client()
    if client is None:
        return []

    query = client.collection(COLLECTION_NAME)
    if status:
        query = query.where("approval_status", "==", status)

    docs = query.stream()
    rows = [doc.to_dict() for doc in docs if doc.exists]
    rows.sort(key=lambda x: int(x.get("id", 0)), reverse=True)
    return rows[:limit]


def get_firestore_email_by_local_id(email_id: int) -> Optional[dict]:
    """Fetch one email from Firestore using local numeric id."""
    client = _firestore_client()
    if client is None:
        return None
    query = client.collection(COLLECTION_NAME).where("id", "==", email_id).limit(1)
    docs = list(query.stream())
    if not docs:
        return None
    return docs[0].to_dict()


def firestore_email_exists(gmail_message_id: str) -> bool:
    """Check dedupe key existence in Firestore mirror."""
    client = _firestore_client()
    if client is None:
        return False
    doc = client.collection(COLLECTION_NAME).document(gmail_message_id).get()
    return bool(doc.exists)
