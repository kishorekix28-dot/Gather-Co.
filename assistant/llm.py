"""Optional LLM rephrasing, configured purely through environment variables.

The LLM never answers from its own knowledge: it only receives the text that
was already retrieved from the SQL knowledge base and is asked to restate it.
When AI_API_KEY is not set, or the call fails/times out, callers fall back to
the retrieved text verbatim.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("inventory.app")

SYSTEM_PROMPT = (
    "You are the help assistant of an inventory management web app. Answer the user's question using ONLY "
    "the reference text provided. Do not add facts that are not in the reference. Keep it concise (max 120 "
    "words) and keep any step-by-step instructions."
)


def is_configured():
    return bool(settings.AI_API_KEY)


def rephrase(question, reference):
    if not is_configured():
        return None
    user_content = f"Reference text:\n{reference}\n\nUser question: {question}"
    try:
        if settings.AI_PROVIDER == "anthropic":
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.AI_API_KEY, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": settings.AI_MODEL, "max_tokens": 400, "system": SYSTEM_PROMPT,
                      "messages": [{"role": "user", "content": user_content}]},
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            text = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        else:
            resp = requests.post(
                f"{settings.AI_API_BASE.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                json={"model": settings.AI_MODEL, "temperature": 0.2, "max_tokens": 400,
                      "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                   {"role": "user", "content": user_content}]},
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
        text = (text or "").strip()
        return text or None
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError) as exc:
        logger.warning("LLM call failed (%s); using retrieved answer", exc.__class__.__name__)
        return None
