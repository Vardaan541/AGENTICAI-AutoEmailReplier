"""
Polling loop:
- checks Gmail every N seconds
- processes new emails
- stores generated drafts for approval
"""

import time

from app.config import settings
from app.db import email_exists, save_email_record
from app.gmail_client import fetch_unread_emails
from app.openai_client import classify_email, extract_context, generate_reply
from app.safety import is_sensitive_email


def process_incoming_emails() -> int:
    """
    One polling cycle.
    Returns number of newly processed emails.
    """
    unread = fetch_unread_emails(max_results=5)
    new_count = 0

    for email in unread:
        try:
            if email_exists(email["gmail_message_id"]):
                continue

            classification = classify_email(email["subject"], email["body"])
            context = extract_context(email["subject"], email["body"])

            # Never auto-handle sensitive content.
            sensitive = is_sensitive_email(email["subject"], email["body"])
            if sensitive:
                generated_reply = "Manual review required: sensitive content detected."
                approval_status = "rejected"
            elif classification == "Spam":
                generated_reply = "No reply generated: classified as Spam."
                approval_status = "rejected"
            else:
                generated_reply = generate_reply(email["subject"], email["body"], context)
                approval_status = "pending"

            save_email_record(
                {
                    **email,
                    "classification": classification,
                    "intent": context["intent"],
                    "urgency": context["urgency"],
                    "required_action": context["required_action"],
                    "generated_reply": generated_reply,
                    "approval_status": approval_status,
                }
            )
            new_count += 1
        except Exception as exc:  # broad to keep polling robust in production
            print(f"Skipping email {email.get('gmail_message_id')} due to processing error: {exc}")
            continue
    return new_count


def run_polling_loop() -> None:
    """Run forever and process emails every poll interval."""
    print("Email poller started. Press Ctrl+C to stop.")
    while True:
        try:
            count = process_incoming_emails()
            print(f"Processed {count} new emails.")
        except Exception as exc:  # broad for demo robustness
            print(f"Polling error: {exc}")
        time.sleep(settings.poll_interval_seconds)
