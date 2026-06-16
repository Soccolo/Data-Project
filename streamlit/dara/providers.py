"""Provider implementations.

Each provider takes the resolved model id plus the request payload and returns
the model's text output (or a JSON string when a ``schema`` is requested).
``ai_client`` picks which one to call based on the (tier, purpose) routing in
``tiers``.

Structured output: when ``schema`` is set we coerce strict JSON out of each
provider — Gemini via ``responseSchema``, Claude via forced tool-use, DeepSeek
via ``response_format``. History is sanitized so the message list always starts
with a user turn (Claude/Gemini reject a leading assistant/model turn).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

from .config import settings
from .tiers import ModelChoice

_TIMEOUT = 90      # seconds
_MAX_TOKENS = 2048

# Some calls (e.g. an interview opener) have no user text yet. Newer Claude
# models reject whitespace-only text blocks ("text content blocks must contain
# non-whitespace text"), so seed a minimal non-empty kickoff rather than " ".
_KICKOFF = "Let's begin."


def call_provider(choice: ModelChoice, body: Dict[str, Any]) -> str:
    if choice.provider == "anthropic":
        return _call_anthropic(choice.model, body)
    if choice.provider == "google":
        return _call_google(choice.model, body)
    if choice.provider == "deepseek":
        return _call_deepseek(choice.model, body)
    raise ValueError(f"Unknown provider: {choice.provider}")


def _max_tokens(body: Dict[str, Any]) -> int:
    return int(body.get("max_tokens") or _MAX_TOKENS)


def _history_from_user(history: Any) -> List[Dict[str, Any]]:
    """Drop any leading assistant turns so the sequence starts with a user
    message — required by Anthropic and Gemini."""
    msgs = list(history or [])
    while msgs and msgs[0].get("role") == "assistant":
        msgs.pop(0)
    return msgs


# ─── Anthropic ───────────────────────────────────────────────────────
def _call_anthropic(model: str, body: Dict[str, Any]) -> str:
    key = settings.anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    history = _history_from_user(body.get("history"))
    if history:
        messages: List[Dict[str, Any]] = history
    else:
        content: List[Dict[str, Any]] = []
        for m in (body.get("media") or [])[:5]:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": m["mediaType"], "data": m["base64"]}})
        content.append({"type": "text", "text": body.get("userText") or _KICKOFF})
        messages = [{"role": "user", "content": content}]

    payload: Dict[str, Any] = {
        "model": model, "max_tokens": _max_tokens(body),
        "system": body.get("systemPrompt"), "messages": messages,
    }
    # Structured output via a forced tool call — the reliable way to get JSON.
    schema = body.get("schema")
    if schema:
        payload["tools"] = [{
            "name": "respond",
            "description": "Return the answer in the required structure.",
            "input_schema": schema,
        }]
        payload["tool_choice"] = {"type": "tool", "name": "respond"}

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"Content-Type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"},
        json=payload, timeout=_TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Anthropic {r.status_code}: {r.text}")
    data = r.json()
    blocks = data.get("content") or []
    if schema:
        for b in blocks:
            if b.get("type") == "tool_use":
                return json.dumps(b.get("input", {}))
        return "{}"
    for b in blocks:
        if b.get("type") == "text":
            return b.get("text", "")
    return ""


# ─── Google (Gemini) ─────────────────────────────────────────────────
def _call_google(model: str, body: Dict[str, Any]) -> str:
    key = settings.google_api_key
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set")

    history = _history_from_user(body.get("history"))
    if history:
        contents = [{"role": "model" if m["role"] == "assistant" else "user",
                     "parts": [{"text": m["content"]}]} for m in history]
    else:
        parts: List[Dict[str, Any]] = []
        for m in (body.get("media") or [])[:5]:
            parts.append({"inlineData": {"mimeType": m["mediaType"], "data": m["base64"]}})
        parts.append({"text": body.get("userText") or _KICKOFF})
        contents = [{"role": "user", "parts": parts}]

    generation_config: Dict[str, Any] = {"maxOutputTokens": _max_tokens(body)}
    # Gemini 2.5 models "think" by default, which can consume the entire output
    # budget and return empty text — especially on structured calls. Disable it
    # so tokens go to the actual answer.
    if model.startswith("gemini-2.5"):
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}
    if body.get("schema"):
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseSchema"] = body["schema"]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    r = requests.post(
        url, headers={"Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": body.get("systemPrompt")}]},
              "contents": contents, "generationConfig": generation_config},
        timeout=_TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Google {r.status_code}: {r.text}")
    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    return parts[0].get("text", "") if parts else ""


# ─── DeepSeek ────────────────────────────────────────────────────────
def _call_deepseek(model: str, body: Dict[str, Any]) -> str:
    key = settings.deepseek_api_key
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")

    messages: List[Dict[str, Any]] = [{"role": "system", "content": body.get("systemPrompt")}]
    history = _history_from_user(body.get("history"))
    if history:
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})
    else:
        messages.append({"role": "user", "content": body.get("userText") or _KICKOFF})

    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        json={"model": model, "messages": messages, "max_tokens": _max_tokens(body),
              "response_format": {"type": "json_object"} if body.get("schema") else None},
        timeout=_TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"DeepSeek {r.status_code}: {r.text}")
    data = r.json()
    choices = data.get("choices") or []
    return choices[0].get("message", {}).get("content", "") if choices else ""
