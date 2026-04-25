"""Run this file to review/approve generated replies."""

from app.db import init_db
from app.cli import run_approval_cli

if __name__ == "__main__":
    init_db()
    run_approval_cli()
