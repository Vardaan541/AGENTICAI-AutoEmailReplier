"""Run this file to start the background polling loop."""

from app.db import init_db
from app.poller import run_polling_loop

if __name__ == "__main__":
    init_db()
    run_polling_loop()
