# Agentic AI Email Auto-Reply (Beginner Friendly)

This project reads new Gmail emails, classifies them with AI, drafts replies, and asks **you** for approval before sending.

It is built to teach you backend + APIs + AI basics while giving you a real working system.

---

## 0) Tech Stack (Simple Explanation)

### What we are building
We are building a Python app with three main pieces: a web API (`FastAPI`), a local database (`SQLite`), and AI logic (`OpenAI API`).

### Why this is needed
Real products need structure: API for control, database for memory, and AI for language tasks.

### How it works (beginner-friendly)
- **FastAPI**: a framework to create HTTP endpoints (for example `/health` or `/pending`)
- **API (what is an API?)**: a way for programs to talk to each other using requests and responses
- **SQLite (what is a database?)**: a structured file to store records (emails, classifications, replies)

### Code
See:
- `app/main.py` (FastAPI routes)
- `app/db.py` (SQLite table + queries)
- `app/openai_client.py` (AI calls)

### Key Concepts You Learned
- APIs are like software "menus" with predefined actions.
- Databases keep your app state between runs.
- FastAPI quickly turns Python functions into web endpoints.

---

## 1) Gmail Integration with OAuth2

### What we are building
A Gmail connection so our app can read and send emails with your permission.

### Why this is needed
Without Gmail API auth, your app cannot securely access your mailbox.

### How it works (beginner-friendly)
- **OAuth2** means: "Google verifies you and gives this app limited access."
- Instead of sharing your Gmail password, you approve permissions in a browser.
- Google returns a token (`token.json`) that the app uses for future requests.

### Step-by-step Google Cloud setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable **Gmail API**:
   - APIs & Services -> Library -> search "Gmail API" -> Enable.
4. Configure OAuth consent screen:
   - APIs & Services -> OAuth consent screen.
   - Choose External (or Internal if your org supports it).
   - Fill app name + email.
   - Add scopes for Gmail read/send when asked.
5. Create OAuth credentials:
   - APIs & Services -> Credentials -> Create Credentials -> OAuth client ID.
   - Application type: Desktop app.
   - Download JSON and rename to `credentials.json`.
6. Put `credentials.json` in project root.
7. First run opens browser login; after approval, `token.json` is generated automatically.

### Code
Gmail auth and API calls are in `app/gmail_client.py`.

### Key Concepts You Learned
- OAuth2 gives secure delegated access (without sharing password).
- Scopes control what your app is allowed to do.
- `credentials.json` starts auth; `token.json` stores approved session.

---

## 2) Email Monitoring (Polling)

### What we are building
A loop that checks Gmail every few seconds for unread emails.

### Why this is needed
Polling is simpler than webhooks for beginners: no public server URL, no callback setup.

### How it works (beginner-friendly)
- Polling means: "ask repeatedly" (example: every 30 seconds).
- Each cycle:
  1. fetch unread emails
  2. skip already processed messages
  3. classify + draft reply
  4. save to database for approval

### Code
See `app/poller.py` and `run_poller.py`.

### Key Concepts You Learned
- Polling trades simplicity for extra API calls.
- Loop + sleep is a common automation pattern.
- Deduplication (`email_exists`) prevents reprocessing.

---

## 3) Email Classification with OpenAI

### What we are building
AI classification into:
- Important
- Informational
- Spam

### Why this is needed
Not every email deserves the same attention. Classification helps prioritize and filter.

### How it works (beginner-friendly)
- **LLM (Large Language Model)**: an AI trained on large text data that understands language patterns.
- We send subject + body to OpenAI with clear instructions.
- The model returns JSON like `{"classification": "Important"}`.

### Code
See `classify_email()` inside `app/openai_client.py`.

### Key Concepts You Learned
- LLMs can do structured NLP tasks, not just chat.
- JSON output makes AI responses easier to consume in code.
- We validate the label to avoid bad model outputs.

---

## 4) Context Understanding (Intent, Urgency, Action)

### What we are building
Extraction of:
- sender (from Gmail headers)
- intent
- urgency
- required action

### Why this is needed
A good reply needs context, not just raw text.

### How it works (beginner-friendly)
- **Text parsing**: we parse sender/subject/body from Gmail payload.
- **LLM reasoning**: AI infers intent and urgency from wording.
- We store these fields in SQLite to inspect later.

### Code
See:
- `fetch_unread_emails()` in `app/gmail_client.py`
- `extract_context()` in `app/openai_client.py`

### Key Concepts You Learned
- Parsing extracts explicit data.
- LLM reasoning infers implicit meaning.
- Storing context enables audit and debugging.

---

## 5) Reply Generation + Prompt Engineering

### What we are building
An AI-generated email draft based on the incoming message and extracted context.

### Why this is needed
Automated drafting saves time while maintaining professional tone.

### How it works (beginner-friendly)
- **Prompt engineering** means writing better instructions for AI.
- We provide:
  - original subject/body
  - extracted context
  - style instructions (polite, concise, ask clarification if needed)
- Model returns draft reply text.

### Code
See `generate_reply()` in `app/openai_client.py`.

### Key Concepts You Learned
- Better prompts produce better outputs.
- Context-rich prompts improve relevance.
- Temperature controls creativity vs consistency.

---

## 6) Approval System (Human-in-the-Loop CLI)

### What we are building
A command-line reviewer where you can:
- approve
- edit
- reject
- skip

### Why this is needed
Human-in-the-loop prevents risky automatic responses and keeps quality high.

### How it works (beginner-friendly)
- App loads `pending` replies from SQLite.
- You inspect email + AI draft.
- Your action decides whether a reply is sent.

### Code
See `app/cli.py` and `run_cli.py`.

### Key Concepts You Learned
- AI should assist, not blindly act.
- Approval checkpoints reduce mistakes.
- Editable drafts combine speed + control.

---

## 7) Sending Emails

### What we are building
Sending approved replies back through Gmail API.

### Why this is needed
Drafting is only useful if the approved response can be delivered.

### How it works (beginner-friendly)
- We create a MIME email object.
- Encode it to base64 (required by Gmail API format).
- Call `gmail.users().messages().send(...)`.

### Code
See `send_reply()` in `app/gmail_client.py`.

### Key Concepts You Learned
- Email has standard message formats (MIME).
- APIs often require specific encoding and payload structure.
- Thread ID keeps replies linked to conversation.

---

## 8) Safety Rules

### What we are building
A basic guardrail system that blocks auto-replies on sensitive topics.

### Why this is needed
Automation can create security/privacy/legal risks if unmanaged.

### How it works (beginner-friendly)
- Keyword check detects risky content (password, OTP, bank details, etc.).
- Sensitive emails are marked for manual handling.
- Spam is also blocked from reply generation.

### Code
See `app/safety.py` and related checks in `app/poller.py`.

### Key Concepts You Learned
- Safety rules are mandatory in automation.
- Rule-based checks are simple and effective starting point.
- You can layer rule checks with AI checks for stronger protection.

---

## 9) Folder-by-Folder Architecture

### What we are building
A clean project structure that separates concerns.

### Why this is needed
Organized folders make scaling and debugging easier.

### How it works (beginner-friendly)
- `app/config.py`: loads environment settings
- `app/db.py`: manages SQLite storage
- `app/gmail_client.py`: Gmail authentication/read/send
- `app/openai_client.py`: AI classification/context/reply
- `app/safety.py`: security rules
- `app/poller.py`: recurring inbox processing
- `app/cli.py`: approval workflow
- `app/main.py`: FastAPI endpoints
- `run_poller.py`: starts polling service
- `run_cli.py`: starts manual approval interface

### Code
Explore each file in the project root and `app/`.

### Key Concepts You Learned
- "Single responsibility" design improves maintainability.
- Data flow across modules is easier to reason about.
- Entry scripts (`run_*.py`) simplify operations.

---

## 10) Installation and Run Guide

### What we are building
A complete local setup so you can run and test the system.

### Why this is needed
Even good code is useless without reliable run instructions.

### How it works (beginner-friendly)
Follow these steps in order:

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Setup env:
```bash
cp .env.example .env
```
Edit `.env` with your OpenAI key and optional values.

4. Add Google OAuth file:
- Put `credentials.json` in project root.

5. Start API server:
```bash
uvicorn app.main:app --reload
```

6. In another terminal, start poller:
```bash
python run_poller.py
```

7. Review and approve drafts:
```bash
python run_cli.py
```

### Key Concepts You Learned
- Backend apps usually run multiple processes.
- Environment variables keep secrets out of code.
- Terminal workflows are core backend skills.

---

## 11) Common Errors and Fixes

### What we are building
A quick troubleshooting guide for beginner blockers.

### Why this is needed
Most learning time is spent debugging setup issues.

### How it works (beginner-friendly)

1. **`FileNotFoundError: credentials.json`**
   - Fix: place downloaded Google OAuth JSON in project root.

2. **`invalid_scope` or Gmail permission errors**
   - Fix: ensure Gmail API enabled and scopes allowed in consent screen.
   - Delete `token.json` and re-authenticate if scope changed.

3. **OpenAI authentication error**
   - Fix: verify `OPENAI_API_KEY` in `.env`.
   - Make sure virtualenv is active before running.

4. **No pending emails in CLI**
   - Fix: run poller first, and ensure inbox has unread non-promotional mails.

5. **`ModuleNotFoundError` for app files**
   - Fix: run commands from project root and activate `.venv`.

### Key Concepts You Learned
- Most backend issues are config/auth/path related.
- Reading exact error messages gives strong clues.
- Small iterative fixes beat random trial-and-error.

---

## 12) Next Improvements (Intermediate Level)

- Add attachment parsing and handling.
- Add better safety checks (PII detection model).
- Add UI dashboard for approvals.
- Add unit tests and logging.
- Add scheduler + deployment (Render/Railway/AWS).

You now have a strong beginner-to-intermediate foundation in APIs, OAuth, polling systems, AI prompting, and safe automation workflows.

---

## 13) Flutter App + Firebase (New)

You now also have a mobile app scaffold in `flutter_app/` and backend API endpoints for app-driven approvals.

### Backend API changes
- New protected endpoints in `app/main.py`:
  - `GET /emails`
  - `GET /pending`
  - `POST /emails/{id}/approve`
  - `POST /emails/{id}/edit-and-approve`
  - `POST /emails/{id}/reject`
  - `POST /poll-once`
- Firebase ID token verification added via `app/firebase_auth.py`.
- If `FIREBASE_SERVICE_ACCOUNT_FILE` is missing, backend allows dev mode (unprotected requests).

### Backend setup
1. Install updated dependencies:
```bash
pip install -r requirements.txt
```
2. Add this in `.env`:
```bash
FIREBASE_SERVICE_ACCOUNT_FILE=firebase-service-account.json
GMAIL_WEB_CLIENT_ID=<google_oauth_web_client_id>
GMAIL_WEB_CLIENT_SECRET=<google_oauth_web_client_secret>
```
3. Download Firebase service account JSON for project `email-agentic-ai` and place it at project root as `firebase-service-account.json`.
4. Start API:
```bash
uvicorn app.main:app --reload
```

### Flutter app setup
1. Open `flutter_app/` in terminal.
2. Add your Firebase app config files:
   - Android: `android/app/google-services.json`
   - iOS: `ios/Runner/GoogleService-Info.plist`
3. Install packages:
```bash
flutter pub get
```
4. Run app with API URL:
```bash
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```
For long-lived per-user Gmail access (refresh token exchange), also pass Google OAuth web client id:
```bash
flutter run \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
  --dart-define=GOOGLE_SERVER_CLIENT_ID=<google_oauth_web_client_id>
```

### How it works now
- Poller can keep running in backend (`python run_poller.py`) to fetch/generate drafts.
- Flutter app shows pending drafts and lets you approve/reject/edit+approve directly from UI.
- Backend still uses SQLite for primary app reads, and now mirrors records/status updates to Firestore (`email_records` collection) whenever Firebase service account is configured.

### Optional Firebase read mode
You can now read records from Firestore directly by using query param `source=firebase`:
- `GET /pending?source=firebase`
- `GET /emails?source=firebase`
- `GET /emails?status=pending&source=firebase`

Storage capability endpoint:
- `GET /storage-status`

---

## 14) Run Anytime on Phone (Cloud Deployment)

To stop using local commands (`uvicorn`, `run_poller.py`) and run this app anytime, deploy backend to Google Cloud Run and trigger polling with Cloud Scheduler.

### What changed in code for production
- Added Docker support:
  - `Dockerfile`
  - `.dockerignore`
- Added scheduler-safe polling endpoint:
  - `POST /jobs/poll` in `app/main.py`
  - Protected by header `x-job-secret` that must match `POLL_JOB_SECRET`
- API now defaults to Firestore-backed reads (`source=firebase`) and falls back to SQLite if needed.

### Required env vars (Cloud Run)
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `POLL_JOB_SECRET`
- `FIREBASE_SERVICE_ACCOUNT_FILE` (path in container)
- `GMAIL_CREDENTIALS_FILE` (path in container)
- `GMAIL_TOKEN_FILE` (path in container)

### Important file note
For production, do **not** bake secret files into Docker image. Mount secrets or inject them via secret manager/volumes and point env vars to those mounted paths.

### Deploy to Cloud Run (example)
```bash
# 1) Set project and region
gcloud config set project email-agentic-ai
gcloud config set run/region asia-south1

# 2) Build and push container
gcloud builds submit --tag gcr.io/email-agentic-ai/email-agentic-api

# 3) Deploy Cloud Run service
gcloud run deploy email-agentic-api \
  --image gcr.io/email-agentic-ai/email-agentic-api \
  --allow-unauthenticated \
  --set-env-vars GROQ_MODEL=llama-3.1-8b-instant,POLL_JOB_SECRET=replace_with_strong_secret
```

### Create scheduler job (replaces run_poller.py)
```bash
gcloud scheduler jobs create http email-poll-job \
  --location asia-south1 \
  --schedule "*/2 * * * *" \
  --uri "https://<YOUR_CLOUD_RUN_URL>/jobs/poll" \
  --http-method POST \
  --headers "x-job-secret=replace_with_strong_secret"
```

### Point Flutter app to cloud backend
Use your Cloud Run URL instead of localhost:
```bash
flutter run --dart-define=API_BASE_URL=https://<YOUR_CLOUD_RUN_URL>
```

Then build release and install/store-publish app. At that point, your phone app works without your laptop terminal processes.

### Secret Manager hardening (recommended + applied)
- Store these values in Google Secret Manager and map them to Cloud Run env vars:
  - `GROQ_API_KEY`
  - `GMAIL_CREDENTIALS_JSON`
  - `GMAIL_TOKEN_JSON`
  - `POLL_JOB_SECRET`
- Keep only non-secret config as plain env vars (example `GROQ_MODEL`).
- This avoids plaintext secrets in Cloud Run revision environment settings.
