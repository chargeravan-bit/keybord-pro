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


# ---------------------------------------------------------------------------
# QThread worker
# ---------------------------------------------------------------------------

class AiBrainWorker(QThread):
    """
    Runs the screenshot → AI query pipeline on a background thread.
    Emits `result` with the answer text, or `error` with an error message.
    """

    result = Signal(str)
    error  = Signal(str)
    status = Signal(str)   # short progress messages for the overlay

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
            logger.info("AI Brain: capturing screen")
            screenshot_b64 = capture_screen_base64()

            self.status.emit("📋  Reading clipboard…")
            clipboard_text = get_clipboard_text()
            logger.info(
                "AI Brain: clipboard has %d chars", len(clipboard_text)
            )

            self.status.emit("🧠  Thinking…")
            logger.info(
                "AI Brain: querying %s @ %s", self._model, self._base_url
            )
            answer = query_ai(
                api_key=self._api_key,
                base_url=self._base_url,
                model=self._model,
                screenshot_b64=screenshot_b64,
                clipboard_text=clipboard_text,
            )
            logger.info("AI Brain: got response (%d chars)", len(answer))
            self.result.emit(answer)

        except Exception as exc:
            logger.error("AI Brain error: %s", exc, exc_info=True)
            self.error.emit(str(exc))
