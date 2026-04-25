"""FastAPI entrypoint with mobile-friendly endpoints."""

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from urllib.error import HTTPError, URLError
from pydantic import BaseModel, Field

from app.db import (
    get_email_by_id,
    get_user_gmail_token,
    init_db,
    list_emails,
    list_pending_emails,
    list_pending_emails_by_owner,
    update_approval_status,
    upsert_user_gmail_token,
)
from app.config import settings
from app.firestore_sync import firestore_enabled, get_firestore_email_by_local_id, list_firestore_emails
from app.firebase_auth import verify_firebase_user
from app.gmail_client import exchange_auth_code_for_tokens, send_reply
from app.poller import process_incoming_emails

app = FastAPI(title="Agentic AI Email Auto Reply API")


class EditReplyRequest(BaseModel):
    reply_text: str = Field(min_length=1, description="Edited reply text to send")


class GmailConnectRequest(BaseModel):
    access_token: str = Field(min_length=1, description="User Gmail OAuth access token")
    refresh_token: str = Field(default="", description="Optional Gmail OAuth refresh token")
    token_uri: str = Field(default="https://oauth2.googleapis.com/token")
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    expiry: str = Field(default="")


class GmailAuthCodeRequest(BaseModel):
    server_auth_code: str = Field(min_length=1, description="Google server auth code")


def _extract_email_address(sender: str) -> str:
    if "<" in sender and ">" in sender:
        return sender.split("<")[-1].replace(">", "").strip()
    return sender.strip()


def _get_email_record(email_id: int, owner_uid: Optional[str] = None) -> Optional[dict]:
    """Read email from SQLite first, then Firestore mirror fallback."""
    row = get_email_by_id(email_id, owner_uid=owner_uid)
    if row:
        return dict(row)
    if firestore_enabled():
        fs_row = get_firestore_email_by_local_id(email_id, owner_uid=owner_uid)
        if fs_row:
            return fs_row
    return None


def _gmail_token_from_header_or_store(user: dict, x_gmail_access_token: Optional[str]) -> Optional[dict]:
    email = (user.get("email") or "").strip()
    uid = (user.get("uid") or "").strip()
    if not uid:
        return None

    header_token = (x_gmail_access_token or "").strip()
    if header_token:
        token_info = {
            "access_token": header_token,
            "refresh_token": "",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "",
            "client_secret": "",
            "scopes": "gmail.readonly,gmail.send",
            "expiry": "",
        }
        upsert_user_gmail_token(uid=uid, email=email, token_info=token_info)
        return token_info

    stored = get_user_gmail_token(uid)
    if not stored:
        return None
    return {
        "access_token": stored.get("access_token", ""),
        "refresh_token": stored.get("refresh_token", ""),
        "token_uri": stored.get("token_uri", "https://oauth2.googleapis.com/token"),
        "client_id": stored.get("client_id", ""),
        "client_secret": stored.get("client_secret", ""),
        "scopes": stored.get("scopes", ""),
        "expiry": stored.get("expiry", ""),
    }


def _verify_poll_job_secret(x_job_secret: Optional[str] = Header(default=None)) -> None:
    """
    Lightweight auth for scheduler-triggered poll endpoint.
    Configure POLL_JOB_SECRET in Cloud Run + Scheduler header.
    """
    expected = settings.poll_job_secret.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="POLL_JOB_SECRET not configured on server.",
        )
    if x_job_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid scheduler job secret.",
        )


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/gmail/connect")
def connect_gmail(
    payload: GmailConnectRequest,
    user: dict = Depends(verify_firebase_user),
) -> dict:
    uid = (user.get("uid") or "").strip()
    email = (user.get("email") or "").strip()
    if not uid:
        raise HTTPException(status_code=400, detail="Authenticated user uid missing.")
    token_info = {
        "access_token": payload.access_token,
        "refresh_token": payload.refresh_token,
        "token_uri": payload.token_uri,
        "client_id": payload.client_id,
        "client_secret": payload.client_secret,
        "scopes": "gmail.readonly,gmail.send",
        "expiry": payload.expiry,
    }
    upsert_user_gmail_token(uid=uid, email=email, token_info=token_info)
    return {"status": "connected", "uid": uid, "email": email}


@app.post("/auth/gmail/exchange-code")
def exchange_gmail_code(
    payload: GmailAuthCodeRequest,
    user: dict = Depends(verify_firebase_user),
) -> dict:
    uid = (user.get("uid") or "").strip()
    email = (user.get("email") or "").strip()
    if not uid:
        raise HTTPException(status_code=400, detail="Authenticated user uid missing.")
    try:
        token_info = exchange_auth_code_for_tokens(payload.server_auth_code.strip())
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPError as exc:
        reason = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {reason}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Network error during token exchange: {exc}") from exc
    upsert_user_gmail_token(uid=uid, email=email, token_info=token_info)
    return {"status": "connected_with_refresh_token", "uid": uid, "email": email}


@app.post("/poll-once")
def poll_once(
    user: dict = Depends(verify_firebase_user),
    x_gmail_access_token: Optional[str] = Header(default=None),
) -> dict:
    uid = (user.get("uid") or "").strip()
    email = (user.get("email") or "").strip()
    token_info = _gmail_token_from_header_or_store(user, x_gmail_access_token)
    if not token_info:
        raise HTTPException(status_code=400, detail="Gmail token missing. Reconnect Google account.")
    processed = process_incoming_emails(owner_uid=uid, owner_email=email, token_info=token_info)
    return {"processed_count": processed}


@app.post("/jobs/poll")
def poll_from_scheduler(_: None = Depends(_verify_poll_job_secret)) -> dict:
    """
    Cloud Scheduler-safe polling trigger.
    This replaces local run_poller.py usage in production.
    """
    processed = process_incoming_emails()
    return {"processed_count": processed, "trigger": "scheduler"}


@app.get("/emails")
def emails(
    status: Optional[str] = None,
    source: str = "firebase",
    user: dict = Depends(verify_firebase_user),
) -> list[dict]:
    uid = (user.get("uid") or "").strip()
    if source == "firebase":
        firebase_status = "pending" if status == "pending" else None
        rows = list_firestore_emails(status=firebase_status, limit=100, owner_uid=uid)
        if rows:
            return rows

    if status == "pending":
        rows = list_pending_emails_by_owner(uid)
    else:
        rows = list_emails(limit=100, owner_uid=uid)
    return [dict(row) for row in rows]


@app.get("/pending")
def pending(source: str = "firebase", user: dict = Depends(verify_firebase_user)) -> list[dict]:
    uid = (user.get("uid") or "").strip()
    if source == "firebase":
        rows = list_firestore_emails(status="pending", limit=100, owner_uid=uid)
        if rows:
            return rows

    rows = list_pending_emails_by_owner(uid)
    return [dict(row) for row in rows]


@app.get("/storage-status")
def storage_status(_: dict = Depends(verify_firebase_user)) -> dict:
    return {
        "sqlite": True,
        "firebase_enabled": firestore_enabled(),
        "read_sources": ["sqlite", "firebase"],
    }


@app.post("/emails/{email_id}/approve")
def approve_email(
    email_id: int,
    user: dict = Depends(verify_firebase_user),
    x_gmail_access_token: Optional[str] = Header(default=None),
) -> dict:
    uid = (user.get("uid") or "").strip()
    row = _get_email_record(email_id, owner_uid=uid)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row["approval_status"] != "pending":
        raise HTTPException(status_code=400, detail="Email is not pending")

    token_info = _gmail_token_from_header_or_store(user, x_gmail_access_token)
    if not token_info:
        raise HTTPException(status_code=400, detail="Gmail token missing. Reconnect Google account.")
    to_address = _extract_email_address(row["sender"])
    send_reply(row["thread_id"], to_address, row["subject"], row["generated_reply"], token_info=token_info)
    update_approval_status(email_id, "approved")
    return {"status": "approved", "email_id": email_id}


@app.post("/emails/{email_id}/edit-and-approve")
def edit_and_approve_email(
    email_id: int,
    payload: EditReplyRequest,
    user: dict = Depends(verify_firebase_user),
    x_gmail_access_token: Optional[str] = Header(default=None),
) -> dict:
    uid = (user.get("uid") or "").strip()
    row = _get_email_record(email_id, owner_uid=uid)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row["approval_status"] != "pending":
        raise HTTPException(status_code=400, detail="Email is not pending")

    token_info = _gmail_token_from_header_or_store(user, x_gmail_access_token)
    if not token_info:
        raise HTTPException(status_code=400, detail="Gmail token missing. Reconnect Google account.")
    to_address = _extract_email_address(row["sender"])
    send_reply(row["thread_id"], to_address, row["subject"], payload.reply_text, token_info=token_info)
    update_approval_status(email_id, "approved", edited_reply=payload.reply_text)
    return {"status": "approved", "email_id": email_id, "edited": True}


@app.post("/emails/{email_id}/reject")
def reject_email(email_id: int, user: dict = Depends(verify_firebase_user)) -> dict:
    uid = (user.get("uid") or "").strip()
    row = _get_email_record(email_id, owner_uid=uid)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row["approval_status"] != "pending":
        raise HTTPException(status_code=400, detail="Email is not pending")

    update_approval_status(email_id, "rejected")
    return {"status": "rejected", "email_id": email_id}
