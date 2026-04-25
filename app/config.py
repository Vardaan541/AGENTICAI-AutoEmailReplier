"""
Central place for environment configuration.
Beginner tip: keeping config in one file avoids hard-coding values all over your project.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load values from a local .env file if present.
load_dotenv()


@dataclass
class Settings:
    # Groq setup
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Gmail OAuth files
    gmail_credentials_file: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    gmail_token_file: str = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    gmail_credentials_json: str = os.getenv("GMAIL_CREDENTIALS_JSON", "")
    gmail_token_json: str = os.getenv("GMAIL_TOKEN_JSON", "")

    # Polling behavior
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))

    # Optional metadata
    approver_email: str = os.getenv("APPROVER_EMAIL", "")

    # Firebase Admin (backend auth verification)
    firebase_service_account_file: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", "")

    # Scheduler trigger secret (for cloud polling job endpoint)
    poll_job_secret: str = os.getenv("POLL_JOB_SECRET", "")


settings = Settings()
