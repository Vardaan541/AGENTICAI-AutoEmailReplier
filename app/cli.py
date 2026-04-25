"""
CLI approval tool (human-in-the-loop).
Allows approve / edit / reject decisions before sending emails.
"""

from app.db import list_pending_emails, update_approval_status
from app.gmail_client import send_reply


def _extract_email_address(sender: str) -> str:
    """
    Convert 'Name <email@x.com>' into 'email@x.com'.
    If angle brackets are absent, return original text.
    """
    if "<" in sender and ">" in sender:
        return sender.split("<")[-1].replace(">", "").strip()
    return sender.strip()


def run_approval_cli() -> None:
    """Interactive loop for pending email approvals."""
    pending = list_pending_emails()
    if not pending:
        print("No pending emails.")
        return

    for row in pending:
        print("\n" + "=" * 60)
        print(f"Local ID: {row['id']}")
        print(f"Sender: {row['sender']}")
        print(f"Subject: {row['subject']}")
        print(f"Classification: {row['classification']}")
        print(f"Intent: {row['intent']}")
        print(f"Urgency: {row['urgency']}")
        print(f"Required Action: {row['required_action']}")
        print("\n--- Original Email ---")
        print(row["body"][:1200])  # avoid flooding the terminal
        print("\n--- Generated Reply ---")
        print(row["generated_reply"])
        print("\nChoose: [a]pprove, [e]dit, [r]eject, [s]kip")
        choice = input("Your choice: ").strip().lower()

        if choice == "a":
            to_address = _extract_email_address(row["sender"])
            send_reply(row["thread_id"], to_address, row["subject"], row["generated_reply"])
            update_approval_status(row["id"], "approved")
            print("Reply sent and marked approved.")
        elif choice == "e":
            print("\nEnter your edited reply (single paragraph preferred):")
            edited = input("> ").strip()
            if not edited:
                print("Empty reply. Skipped.")
                continue
            to_address = _extract_email_address(row["sender"])
            send_reply(row["thread_id"], to_address, row["subject"], edited)
            update_approval_status(row["id"], "approved", edited_reply=edited)
            print("Edited reply sent and marked approved.")
        elif choice == "r":
            update_approval_status(row["id"], "rejected")
            print("Email marked rejected (no reply sent).")
        else:
            print("Skipped.")
