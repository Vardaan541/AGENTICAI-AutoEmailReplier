"""
SQLite database helpers.
We use SQLite because it is simple and requires no separate server.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from app.firestore_sync import firestore_email_exists, sync_approval_status, sync_email_record

DB_PATH = Path("email_agent.db")


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Create required tables if they do not exist.
    This runs every startup and is safe because of IF NOT EXISTS.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_message_id TEXT UNIQUE,
            thread_id TEXT,
            sender TEXT,
            subject TEXT,
            body TEXT,
            classification TEXT,
            intent TEXT,
            urgency TEXT,
            required_action TEXT,
            generated_reply TEXT,
            approval_status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def email_exists(gmail_message_id: str) -> bool:
    """Check if we already processed this Gmail message."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM emails WHERE gmail_message_id = ?", (gmail_message_id,))
    row = cursor.fetchone()
    conn.close()
    if row is not None:
        return True
    # Cloud-safe fallback: dedupe across ephemeral container restarts.
    return firestore_email_exists(gmail_message_id)


def save_email_record(record: dict) -> int:
    """Save one processed email and return local database id."""
    conn = get_connection()
    cursor = conn.cursor()
    new_id = 0
    try:
        cursor.execute(
            """
            INSERT INTO emails (
                gmail_message_id, thread_id, sender, subject, body,
                classification, intent, urgency, required_action,
                generated_reply, approval_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["gmail_message_id"],
                record.get("thread_id", ""),
                record.get("sender", ""),
                record.get("subject", ""),
                record.get("body", ""),
                record.get("classification", ""),
                record.get("intent", ""),
                record.get("urgency", ""),
                record.get("required_action", ""),
                record.get("generated_reply", ""),
                record.get("approval_status", "pending"),
            ),
        )
        conn.commit()
        new_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        # Duplicate insert race; fetch existing id and continue.
        cursor.execute("SELECT id FROM emails WHERE gmail_message_id = ?", (record["gmail_message_id"],))
        existing = cursor.fetchone()
        new_id = int(existing["id"]) if existing else 0
    except sqlite3.OperationalError:
        # Cloud environments may hit transient SQLite locks; continue with Firestore mirror.
        new_id = 0
    finally:
        conn.close()
    # Mirror to Firestore when configured.
    sync_email_record({**record, "id": int(new_id)})
    return int(new_id)


def list_pending_emails() -> list[sqlite3.Row]:
    """Get emails waiting for human approval."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails WHERE approval_status = 'pending' ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_email_by_id(email_id: int) -> Optional[sqlite3.Row]:
    """Get one email record by local id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def list_emails(limit: int = 100) -> list[sqlite3.Row]:
    """List recent emails for app UI."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_approval_status(email_id: int, status: str, edited_reply: Optional[str] = None) -> None:
    """Update human approval decision."""
    conn = get_connection()
    cursor = conn.cursor()
    if edited_reply is not None:
        cursor.execute(
            "UPDATE emails SET approval_status = ?, generated_reply = ? WHERE id = ?",
            (status, edited_reply, email_id),
        )
    else:
        cursor.execute("UPDATE emails SET approval_status = ? WHERE id = ?", (status, email_id))
    cursor.execute("SELECT gmail_message_id FROM emails WHERE id = ?", (email_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    if row:
        sync_approval_status(row["gmail_message_id"], status, edited_reply=edited_reply)
