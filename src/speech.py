"""Speech helpers: speech-to-text goes through the active provider; TTS uses gTTS (optional)."""
from __future__ import annotations

import io
import re


def clean_for_speech(text: str, limit: int = 500) -> str:
    t = re.sub(r"[`*_#>]", "", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def synthesize(text: str, lang: str = "en") -> tuple[bytes | None, str]:
    """Return (mp3_bytes, error_message). Never raises; caller falls back to text."""
    spoken = clean_for_speech(text)
    if not spoken:
        return None, ""
    try:
        from gtts import gTTS
    except ImportError:
        return None, "Text-to-speech is not installed (pip install gTTS). Showing text only."
    try:
        buf = io.BytesIO()
        gTTS(text=spoken, lang=lang).write_to_fp(buf)
        return buf.getvalue(), ""
    except Exception:
        return None, "Voice playback is unavailable right now (needs internet). Showing text only."
