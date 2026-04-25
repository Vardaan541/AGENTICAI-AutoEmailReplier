"""FastAPI entrypoint with mobile-friendly endpoints."""

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.db import get_email_by_id, init_db, list_emails, list_pending_emails, update_approval_status
from app.config import settings
from app.firestore_sync import firestore_enabled, get_firestore_email_by_local_id, list_firestore_emails
from app.firebase_auth import verify_firebase_user
from app.gmail_client import send_reply
from app.poller import process_incoming_emails

app = FastAPI(title="Agentic AI Email Auto Reply API")


class EditReplyRequest(BaseModel):
    reply_text: str = Field(min_length=1, description="Edited reply text to send")


def _extract_email_address(sender: str) -> str:
    if "<" in sender and ">" in sender:
        return sender.split("<")[-1].replace(">", "").strip()
    return sender.strip()


def _get_email_record(email_id: int) -> Optional[dict]:
    """Read email from SQLite first, then Firestore mirror fallback."""
    row = get_email_by_id(email_id)
    if row:
        return dict(row)
    if firestore_enabled():
        fs_row = get_firestore_email_by_local_id(email_id)
        if fs_row:
            return fs_row
    return None


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


@app.post("/poll-once")
def poll_once(_: dict = Depends(verify_firebase_user)) -> dict:
    processed = process_incoming_emails()
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
    _: dict = Depends(verify_firebase_user),
) -> list[dict]:
    if source == "firebase":
        firebase_status = "pending" if status == "pending" else None
        rows = list_firestore_emails(status=firebase_status, limit=100)
        if rows:
            return rows

    if status == "pending":
        rows = list_pending_emails()
    else:
        rows = list_emails(limit=100)
    return [dict(row) for row in rows]


@app.get("/pending")
def pending(source: str = "firebase", _: dict = Depends(verify_firebase_user)) -> list[dict]:
    if source == "firebase":
        rows = list_firestore_emails(status="pending", limit=100)
        if rows:
            return rows

    rows = list_pending_emails()
    return [dict(row) for row in rows]


@app.get("/storage-status")
def storage_status(_: dict = Depends(verify_firebase_user)) -> dict:
    return {
        "sqlite": True,
        "firebase_enabled": firestore_enabled(),
        "read_sources": ["sqlite", "firebase"],
    }


@app.post("/emails/{email_id}/approve")
def approve_email(email_id: int, _: dict = Depends(verify_firebase_user)) -> dict:
    row = _get_email_record(email_id)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row["approval_status"] != "pending":
        raise HTTPException(status_code=400, detail="Email is not pending")

    to_address = _extract_email_address(row["sender"])
    send_reply(row["thread_id"], to_address, row["subject"], row["generated_reply"])
    update_approval_status(email_id, "approved")
    return {"status": "approved", "email_id": email_id}


@app.post("/emails/{email_id}/edit-and-approve")
def edit_and_approve_email(
    email_id: int,
    payload: EditReplyRequest,
    _: dict = Depends(verify_firebase_user),
) -> dict:
    row = _get_email_record(email_id)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row["approval_status"] != "pending":
        raise HTTPException(status_code=400, detail="Email is not pending")

    to_address = _extract_email_address(row["sender"])
    send_reply(row["thread_id"], to_address, row["subject"], payload.reply_text)
    update_approval_status(email_id, "approved", edited_reply=payload.reply_text)
    return {"status": "approved", "email_id": email_id, "edited": True}


@app.post("/emails/{email_id}/reject")
def reject_email(email_id: int, _: dict = Depends(verify_firebase_user)) -> dict:
    row = _get_email_record(email_id)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    if row["approval_status"] != "pending":
        raise HTTPException(status_code=400, detail="Email is not pending")

    update_approval_status(email_id, "rejected")
    return {"status": "rejected", "email_id": email_id}
