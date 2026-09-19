"""
AutoKeyboard Pro — AI Brain Core
Captures the screen and clipboard, sends a multimodal request to any
OpenAI-compatible API endpoint (OpenRouter, OpenAI, Gemini, Custom),
and returns the AI's answer as plain text for auto-typing.

Privacy note: The screenshot and clipboard content are transmitted to the
configured AI provider.  No data is stored locally beyond the app session.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider presets (base_url defaults when user picks a named provider)
# ---------------------------------------------------------------------------
PROVIDER_PRESETS: dict[str, dict] = {
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemma-4-31b-it:free",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
    },
    "Custom": {
        "base_url": "",          # user fills this in
        "default_model": "",
    },
}

# ---------------------------------------------------------------------------
# Free model fallback chain — tried in order when the primary model fails
# Keep this list up to date with models confirmed on openrouter.ai/models
# ---------------------------------------------------------------------------
OPENROUTER_FREE_MODELS: list[str] = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "qwen/qwen3.8-27b:free",
    "deepseek/deepseek-v4-flash-0731:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free",
    "inclusionai/ling-3.0-flash-vl:free",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def capture_screen_base64() -> str:
    """Take a full screenshot and return it as a base64-encoded PNG string."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
    except Exception:
        # Fallback: Qt screenshot
        screen = QApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No screen available for capture")
        qimg = screen.grabWindow(0).toImage()
        buf = io.BytesIO()
        qimg.save(buf, format="PNG")   # type: ignore[arg-type]
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def get_clipboard_text() -> str:
    """Return the current clipboard text, or empty string."""
    clipboard = QApplication.clipboard()
    if clipboard is None:
        return ""
    return clipboard.text() or ""


def query_ai(
    api_key: str,
    base_url: str,
    model: str,
    screenshot_b64: str,
    clipboard_text: str,
    prompt_override: Optional[str] = None,
) -> str:
    """
    Send a multimodal request to any OpenAI-compatible endpoint.
    Returns the assistant's text reply.

    Parameters
    ----------
    api_key       : Bearer token for the API
    base_url      : e.g. "https://openrouter.ai/api/v1"
    model         : Model slug, e.g. "google/gemma-3n-e4b-it:free"
    screenshot_b64: Base-64 PNG of the current screen
    clipboard_text: Text currently in clipboard (may be empty)
    prompt_override: Optional custom system/user prompt (not exposed in v1 UI)
    """
    import json
    import urllib.request
    import urllib.error

    # Build the user message
    user_parts: list[dict] = []

    if clipboard_text.strip():
        user_parts.append({
            "type": "text",
            "text": (
                f"The user has copied the following text to the clipboard:\n\n"
                f"```\n{clipboard_text}\n```\n\n"
            ),
        })

    user_parts.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{screenshot_b64}",
            "detail": "high",
        },
    })

    if prompt_override:
        system_prompt = prompt_override
    else:
        system_prompt = (
            "You are a helpful AI assistant embedded in a keyboard automation tool. "
            "The user has shared a screenshot of their screen and (optionally) some "
            "clipboard text. Analyse what is on the screen and respond helpfully. "
            "If the clipboard contains a question or task, answer it directly. "
            "Keep your response concise and ready to be typed as plain text — "
            "avoid markdown, bullet symbols, or emojis unless specifically asked."
        )

    if not clipboard_text.strip():
        user_parts.append({
            "type": "text",
            "text": "Please look at my screen and tell me what I should do or answer.",
        })
    else:
        user_parts.append({
            "type": "text",
            "text": "Please answer the question / complete the task shown above.",
        })

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_parts},
        ],
        "max_tokens": 1024,
    }

    endpoint = base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/autokeyboard-pro",
            "X-Title": "AutoKeyboard Pro",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API error {exc.code}: {body}") from exc


def query_ai_text_only(
    api_key: str,
    base_url: str,
    model: str,
    clipboard_text: str,
    prompt_override: Optional[str] = None,
) -> str:
    """
    Text-only fallback — no image attached.
    Used automatically when the chosen model does not support vision.
    """
    import json
    import urllib.request
    import urllib.error

    if prompt_override:
        system_prompt = prompt_override
    else:
        system_prompt = (
            "You are a helpful AI assistant embedded in a keyboard automation tool. "
            "The user has copied some text to their clipboard. "
            "Respond helpfully to the content below. "
            "Keep your response concise and ready to be typed as plain text — "
            "avoid markdown, bullet symbols, or emojis unless specifically asked."
        )

    if clipboard_text.strip():
        user_text = (
            f"The user has copied the following text to their clipboard:\n\n"
            f"{clipboard_text}\n\n"
            "Please answer the question or complete the task above."
        )
    else:
        user_text = (
            "The user triggered the AI Brain hotkey but no text is in their clipboard. "
            "Please greet them and ask what they need help with."
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 1024,
    }

    endpoint = base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/autokeyboard-pro",
            "X-Title": "AutoKeyboard Pro",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API error {exc.code}: {body}") from exc


def _is_vision_error(error_body: str) -> bool:
    """Return True if the HTTP error indicates the model doesn't support images."""
def _classify_error(error_body: str) -> str:
    """
    Classify an API error string.
    Returns: 'vision'  — model does not support images
             'ratelimit' — model is rate-limited / unavailable
             'other'  — unrecoverable error
    """
    lower = error_body.lower()
    vision_keywords = [
        "does not support image", "not support vision", "image_url",
        "multimodal", "not a valid model", "invalid model",
        "model not found", "no endpoints found", "unsupported content",
    ]
    rate_keywords = [
        "rate-limit", "rate limit", "ratelimit", "429",
        "temporarily", "upstream", "retry shortly", "quota",
        "overloaded", "capacity", "provider returned error",
    ]
    if any(k in lower for k in vision_keywords):
        return "vision"
    if any(k in lower for k in rate_keywords):
        return "ratelimit"
    return "other"


def _is_vision_error(error_body: str) -> bool:
    return _classify_error(error_body) == "vision"


def _try_one_model(
    api_key: str,
    base_url: str,
    model: str,
    screenshot_b64: str,
    clipboard_text: str,
) -> str:
    """
    Try vision first, fall back to text-only if vision is not supported.
    Raises RuntimeError with a classified message on failure.
    """
    try:
        return query_ai(
            api_key=api_key,
            base_url=base_url,
            model=model,
            screenshot_b64=screenshot_b64,
            clipboard_text=clipboard_text,
        )
    except RuntimeError as exc:
        if _is_vision_error(str(exc)):
            logger.warning("Model %s: no vision support, trying text-only", model)
            return query_ai_text_only(
                api_key=api_key,
                base_url=base_url,
                model=model,
                clipboard_text=clipboard_text,
            )
        raise


# ---------------------------------------------------------------------------
# QThread worker
# ---------------------------------------------------------------------------

class AiBrainWorker(QThread):
    """
    Runs the screenshot → AI query pipeline on a background thread.

    Strategy:
      1. Try the user's chosen model (vision, then text-only fallback).
      2. If rate-limited or unavailable, automatically cycle through
         OPENROUTER_FREE_MODELS until one responds.
      3. Emit result on success, error on total failure.
    """

    result = Signal(str)
    error  = Signal(str)
    status = Signal(str)

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._api_key  = api_key
        self._base_url = base_url
        self._model    = model

    @Slot()
    def run(self) -> None:
        try:
            self.status.emit("📸  Capturing screen…")
            screenshot_b64 = capture_screen_base64()

            self.status.emit("📋  Reading clipboard…")
            clipboard_text = get_clipboard_text()
            logger.info("AI Brain: clipboard=%d chars", len(clipboard_text))

            # Build the list of models to try:
            # primary model first, then the full free fallback chain
            is_openrouter = "openrouter" in self._base_url.lower()
            fallbacks = (
                [m for m in OPENROUTER_FREE_MODELS if m != self._model]
                if is_openrouter else []
            )
            models_to_try = [self._model] + fallbacks
            total = len(models_to_try)
            last_error = "No models available."

            for idx, model in enumerate(models_to_try, start=1):
                label = f"({idx}/{total})" if total > 1 else ""
                self.status.emit(f"🧠  Thinking… {label}")
                logger.info("AI Brain: trying model %s [%d/%d]", model, idx, total)

                try:
                    answer = _try_one_model(
                        api_key=self._api_key,
                        base_url=self._base_url,
                        model=model,
                        screenshot_b64=screenshot_b64,
                        clipboard_text=clipboard_text,
                    )
                    if not answer:
                        logger.warning("Model %s returned empty response, skipping", model)
                        last_error = f"Model {model} returned an empty response."
                        continue

                    logger.info("AI Brain: success with %s (%d chars)", model, len(answer))
                    self.status.emit(f"✅  Done ({model})")
                    self.result.emit(answer)
                    return

                except RuntimeError as exc:
                    err_msg = str(exc)
                    kind = _classify_error(err_msg)
                    last_error = err_msg
                    if kind == "ratelimit" and idx < total:
                        logger.warning("Model %s rate-limited, trying next…", model)
                        self.status.emit(f"⏳  Rate-limited, trying next model… ({idx}/{total})")
                        continue
                    elif kind == "other" or idx == total:
                        # Unrecoverable or last model
                        raise RuntimeError(last_error) from exc
                    # vision error already handled by _try_one_model

            # All models exhausted
            raise RuntimeError(
                f"All {total} models failed or were rate-limited.\n"
                f"Last error: {last_error}\n\n"
                "Tip: Wait a minute and try again, or get a paid API key."
            )

        except Exception as exc:
            logger.error("AI Brain error: %s", exc, exc_info=True)
            self.error.emit(str(exc))
