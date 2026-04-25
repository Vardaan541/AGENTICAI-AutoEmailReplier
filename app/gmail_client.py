"""
Gmail API integration.
Includes:
1) OAuth login flow
2) Reading unread emails
3) Sending reply emails
"""

import base64
import json
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

# Gmail permissions (scopes) needed by this project.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service():
    """
    Authenticate user with OAuth2 and return Gmail service client.
    OAuth2 (simple meaning): secure "Login with Google" style authorization.
    """
    creds = None
    if settings.gmail_token_json:
        try:
            token_data = json.loads(settings.gmail_token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except json.JSONDecodeError:
            creds = None
    else:
        try:
            creds = Credentials.from_authorized_user_file(settings.gmail_token_file, SCOPES)
        except FileNotFoundError:
            creds = None

    # Refresh token if expired, otherwise run browser-based login flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # In cloud env-var mode, we cannot write token file back.
            if not settings.gmail_token_json:
                with open(settings.gmail_token_file, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
        else:
            if settings.gmail_credentials_json:
                credentials_config = json.loads(settings.gmail_credentials_json)
                flow = InstalledAppFlow.from_client_config(credentials_config, SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(settings.gmail_credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            if not settings.gmail_token_json:
                with open(settings.gmail_token_file, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_header(headers: list[dict], key: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == key.lower():
            return h.get("value", "")
    return ""


def _decode_body(payload: dict) -> str:
    """
    Decode Gmail API body payload.
    Tries direct body first, then multipart parts.
    """
    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []) or []:
        part_data = part.get("body", {}).get("data")
        if part_data:
            return base64.urlsafe_b64decode(part_data).decode("utf-8", errors="ignore")
    return ""


def fetch_unread_emails(max_results: int = 5) -> list[dict]:
    """Fetch a small batch of unread emails."""
    service = get_gmail_service()
    response = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread -category:promotions", maxResults=max_results)
        .execute()
    )
    messages = response.get("messages", [])

    parsed_emails: list[dict] = []
    for msg in messages:
        msg_id = msg["id"]
        full = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        payload = full.get("payload", {})
        headers = payload.get("headers", [])
        parsed_emails.append(
            {
                "gmail_message_id": msg_id,
                "thread_id": full.get("threadId", ""),
                "sender": _extract_header(headers, "From"),
                "subject": _extract_header(headers, "Subject"),
                "body": _decode_body(payload),
            }
        )
    return parsed_emails


def send_reply(thread_id: str, to_address: str, subject: str, body: str) -> None:
    """Send email reply using Gmail API."""
    service = get_gmail_service()
    mime_message = MIMEText(body)
    mime_message["to"] = to_address
    mime_message["subject"] = f"Re: {subject}"

    raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
    message = {"raw": raw_message, "threadId": thread_id}
    try:
        service.users().messages().send(userId="me", body=message).execute()
    except HttpError as exc:
        # If old/stale thread id is invalid, send as a fresh message instead.
        if exc.resp.status == 404:
            service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
            return
        raise
