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
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

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


def get_gmail_service_for_user_token(token_info: dict):
    """
    Build Gmail service using a user-specific token.
    Supports access-token-only mode and refresh-token mode.
    """
    access_token = (token_info.get("access_token") or "").strip()
    if not access_token:
        raise ValueError("Missing user Gmail access token.")

    refresh_token = (token_info.get("refresh_token") or "").strip()
    if refresh_token:
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_info.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=token_info.get("client_id") or None,
            client_secret=token_info.get("client_secret") or None,
            scopes=SCOPES,
        )
    else:
        creds = Credentials(token=access_token, scopes=SCOPES)
    return build("gmail", "v1", credentials=creds)


def exchange_auth_code_for_tokens(server_auth_code: str) -> dict:
    """
    Exchange one-time Google server auth code for access/refresh tokens.
    Requires GMAIL_WEB_CLIENT_ID and GMAIL_WEB_CLIENT_SECRET in backend env.
    """
    client_id = settings.gmail_web_client_id.strip()
    client_secret = settings.gmail_web_client_secret.strip()
    if not client_id or not client_secret:
        raise ValueError("Missing GMAIL_WEB_CLIENT_ID or GMAIL_WEB_CLIENT_SECRET.")

    payload = urlencode(
        {
            "code": server_auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    req = UrlRequest(
        url="https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
    token_response = json.loads(raw)
    return {
        "access_token": token_response.get("access_token", ""),
        "refresh_token": token_response.get("refresh_token", ""),
        "token_uri": token_response.get("token_uri", "https://oauth2.googleapis.com/token"),
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": token_response.get("scope", ""),
        "expiry": "",
    }


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


def fetch_unread_emails(max_results: int = 5, token_info: Optional[dict] = None) -> list[dict]:
    """Fetch a small batch of unread emails."""
    service = get_gmail_service_for_user_token(token_info) if token_info else get_gmail_service()
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


def send_reply(
    thread_id: str,
    to_address: str,
    subject: str,
    body: str,
    token_info: Optional[dict] = None,
) -> None:
    """Send email reply using Gmail API."""
    service = get_gmail_service_for_user_token(token_info) if token_info else get_gmail_service()
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
