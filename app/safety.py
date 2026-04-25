"""
Safety rules for automated replies.
These are simple keyword-based checks for beginner-friendly reliability.
"""

SENSITIVE_KEYWORDS = [
    "password",
    "bank account",
    "social security",
    "otp",
    "confidential",
    "wire transfer",
    "invoice payment",
    "credit card",
]


def is_sensitive_email(subject: str, body: str) -> bool:
    """Return True if email looks sensitive and needs manual handling."""
    text = f"{subject}\n{body}".lower()
    return any(keyword in text for keyword in SENSITIVE_KEYWORDS)
