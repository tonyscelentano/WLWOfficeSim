"""
llm.py — Centralized LLM Client

Single point of contact for all NVIDIA NIM / OpenAI-compatible LLM calls.
Systems import call_llm() or call_llm_json() instead of building their own
client, streaming, fence-stripping, and JSON parsing.

Contract:
  - Environment: NVIDIA_API_KEY or NIM_API_KEY must be set.
  - Returns None / fallback when the LLM is unavailable or errors.
  - Callers supply system_prompt, user_prompt (and optionally messages).
  - Never raises to callers — all exceptions are caught, logged, and return None.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

log = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]

# ── Configuration ─────────────────────────────────────────────────────────────

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-nano-30b-a3b"

# Regex to strip markdown code fences from LLM output
_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.MULTILINE)


def _get_client() -> Any | None:
    """Return a configured OpenAI client, or None if unavailable."""
    api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NIM_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(base_url=NIM_BASE_URL, api_key=api_key)


def is_available() -> bool:
    """True if the LLM can be called (key present + library installed)."""
    api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NIM_API_KEY")
    return bool(api_key and OpenAI is not None)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    return _FENCE_RE.sub("", text).strip()


def _stream_text(completion: Any) -> str:
    """Consume a streaming completion and return the full text."""
    parts: list[str] = []
    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta is not None:
            parts.append(delta)
    return "".join(parts).strip()


# ── Public API ────────────────────────────────────────────────────────────────

def call_llm(
    *,
    system_prompt: str,
    user_prompt: str | None = None,
    messages: list[dict[str, str]] | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.8,
    max_tokens: int = 1024,
    stream: bool = True,
) -> str | None:
    """
    Call the LLM and return raw text. Returns None on any failure.

    Provide EITHER user_prompt (simple 2-message call) OR messages (full
    conversation). If both are given, messages takes precedence.
    """
    client = _get_client()
    if client is None:
        log.warning("LLM unavailable (no API key or openai package).")
        return None

    if messages is None:
        messages = [{"role": "system", "content": system_prompt}]
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )
        if stream:
            return _stream_text(completion)
        else:
            return completion.choices[0].message.content.strip()
    except Exception:
        log.exception("LLM call failed.")
        return None


def call_llm_json(
    *,
    system_prompt: str,
    user_prompt: str | None = None,
    messages: list[dict[str, str]] | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = True,
) -> dict[str, Any] | None:
    """
    Call the LLM and parse the response as JSON. Returns None on failure.

    Handles markdown fence stripping automatically. If JSON parsing fails
    after fence removal, returns None (caller should use its fallback).
    """
    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )
    if raw is None:
        return None

    log.debug("Raw LLM response: %s", raw)
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        log.error("LLM returned non-JSON after fence strip: %.200s", cleaned)
        log.debug("Full cleaned content: %s", cleaned)
        return None
