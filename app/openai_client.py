"""
Groq helper functions for:
1) classification
2) context extraction
3) reply generation
"""

import json

from openai import OpenAI

from app.config import settings

MAX_EMAIL_CHARS_FOR_LLM = 2500


def _ensure_groq_ready() -> None:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")


def _groq_client() -> OpenAI:
    _ensure_groq_ready()
    return OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")


def _extract_json_object(text: str) -> dict:
    """Best-effort JSON parsing to keep flow resilient."""
    cleaned = (text or "").strip()
    if not cleaned:
        return {}
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _truncate_for_llm(text: str) -> str:
    """Keep prompts small enough for Groq free-tier limits."""
    text = text or ""
    if len(text) <= MAX_EMAIL_CHARS_FOR_LLM:
        return text
    return text[:MAX_EMAIL_CHARS_FOR_LLM] + "\n\n[Truncated for model token limits]"


def ask_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Ask Groq model for JSON output.
    If parsing fails, return empty dict so app can continue safely.
    """
    client = _groq_client()
    response = client.chat.completions.create(
        model=settings.groq_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content or "{}"
    return _extract_json_object(text)


def classify_email(subject: str, body: str) -> str:
    """Classify email as Important / Informational / Spam."""
    system = (
        "You are an email classifier. Return JSON with one key: "
        '{"classification": "Important|Informational|Spam"}.'
    )
    user = f"Subject: {subject}\n\nBody:\n{_truncate_for_llm(body)}"
    data = ask_llm_json(system, user)
    label = data.get("classification", "Informational")
    if label not in {"Important", "Informational", "Spam"}:
        return "Informational"
    return label


def extract_context(subject: str, body: str) -> dict:
    """Extract sender intent, urgency, and required action."""
    system = (
        "Extract context from an email. Return JSON keys: "
        "intent, urgency, required_action. Keep answers short."
    )
    user = f"Subject: {subject}\n\nBody:\n{_truncate_for_llm(body)}"
    data = ask_llm_json(system, user)
    return {
        "intent": data.get("intent", "Unknown"),
        "urgency": data.get("urgency", "Medium"),
        "required_action": data.get("required_action", "Review and respond"),
    }


def generate_reply(subject: str, body: str, context: dict) -> str:
    """Generate a polite email reply draft."""
    client = _groq_client()
    prompt = (
        "You are a professional email assistant.\n"
        "Write concise, clear, and polite replies.\n"
        "If request is unclear, ask one clarifying question.\n\n"
        f"Original subject: {subject}\n\n"
        f"Original body:\n{_truncate_for_llm(body)}\n\n"
        f"Extracted context:\n{json.dumps(context)}\n\n"
        "Write a draft reply in plain text."
    )
    response = client.chat.completions.create(
        model=settings.groq_model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": "You write professional email replies."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()
