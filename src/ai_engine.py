"""Model layer. Providers share one interface so Gemini can be swapped for any other model.

Provider contract:
    analyze(transcript, image_png|None, context_text, level, attempt=0) -> dict
    verify(image_png, prior_analysis, context_text) -> dict   (live providers)
    transcribe(audio_bytes, mime) -> str                       (live providers)
"""
from __future__ import annotations

import json
import logging
import os
import re

from . import demo_data

log = logging.getLogger("contextbridge.ai")
LEVELS = ["Beginner", "Intermediate", "Expert"]


class AIError(Exception):
    """Carries a message that is safe to show to the user."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


SYSTEM_PROMPT = """You are ContextBridge, a careful real-time assistant for people who are stuck mid-task
(mostly coding/debugging). You receive what the user SAID plus an image of what they are SHOWING
(screenshot or camera photo) and the session history.

Return ONLY one JSON object with exactly these keys:
{
 "goal": "the user's real objective, one sentence",
 "issue": "the problem you can see (or 'No problem visible' / what is unclear)",
 "location": "where it is (file, line, UI element). Say 'Not visible' if you cannot see it",
 "cause": "root cause in one sentence",
 "explanation": "why it happens, written for the requested EXPLANATION LEVEL",
 "suggested_fix": "one specific fix",
 "action_plan": ["2-4 short numbered-step texts"],
 "confidence": "High|Medium|Low followed by a short reason",
 "requires_approval": true,
 "verification_plan": "how we will check the fix worked",
 "highlight": [x, y, w, h] or null,
 "spoken_summary": "1-2 short sentences suitable for text-to-speech"
}
Rules:
- Never claim certainty when the image is blurry, cropped or ambiguous: lower confidence and say what is missing.
- Do not invent code, lines or UI that you cannot see. If unsure, say so.
- "highlight" is the normalised (0-1) bounding box of the problem area in the image. Use null unless you can
  place it reliably. Never guess coordinates.
- If the user is only asking for an explanation (no problem to fix), set requires_approval=false and action_plan=[].
- If the user refers to "that"/"it", resolve it with the session history.
- If an earlier fix attempt failed, analyse why and propose a DIFFERENT, revised fix.
- You only suggest actions. You never run commands. Set requires_approval=true for anything that edits, runs,
  deletes or sends something.
LEVELS: Beginner = plain language, no jargon, short analogies. Intermediate = technical but easy to follow.
Expert = concise technical diagnosis, terse."""

VERIFY_PROMPT = """You are verifying whether a fix worked. You get the PREVIOUS diagnosis and a NEW image of the
user's current screen. Return ONLY JSON:
{"status": "resolved" | "still_present" | "unclear",
 "evidence": "what in the new image supports your verdict",
 "remaining_issue": "what is still wrong, or empty"}
Use "unclear" if the image does not show enough to decide. Never assume success."""


def parse_json_response(text: str) -> dict | None:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    for cand in (t, t[t.find("{"): t.rfind("}") + 1] if "{" in t else ""):
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _s(v, default="") -> str:
    return str(v).strip() if v not in (None, "") else default


def normalize_analysis(d: dict) -> dict:
    plan = d.get("action_plan") or []
    if isinstance(plan, str):
        plan = [plan]
    out = dict(d)
    out.update({
        "goal": _s(d.get("goal"), "Goal not clearly stated"),
        "issue": _s(d.get("issue"), "No clear issue identified"),
        "location": _s(d.get("location"), "Not visible"),
        "cause": _s(d.get("cause")),
        "explanation": _s(d.get("explanation")),
        "suggested_fix": _s(d.get("suggested_fix"), "No fix suggested"),
        "action_plan": [_s(p) for p in plan if _s(p)][:6],
        "confidence": _s(d.get("confidence"), "Low: not stated"),
        "requires_approval": bool(d.get("requires_approval", True)),
        "verification_plan": _s(d.get("verification_plan")),
        "highlight": d.get("highlight"),
        "spoken_summary": _s(d.get("spoken_summary")),
    })
    return out


def fallback_analysis(text: str) -> dict:
    """Used when the model answers in plain text instead of JSON. Never crashes."""
    return normalize_analysis({
        "goal": "Unclear: structured analysis unavailable", "issue": "See the explanation below",
        "location": "Not visible", "explanation": text.strip() or "The model returned an empty answer.",
        "suggested_fix": "Review the answer, then rephrase or add a clearer screenshot.",
        "action_plan": [], "confidence": "Low: unstructured response",
        "requires_approval": False, "spoken_summary": text.strip()[:300], "fallback": True,
    })


def classify_error(e: Exception) -> AIError:
    msg = str(e).lower()
    log.warning("AI call failed: %s", type(e).__name__)
    if any(k in msg for k in ("api key", "api_key", "401", "403", "permission", "unauthenticated")):
        return AIError("The API key was rejected. Check GEMINI_API_KEY in your .env file.")
    if any(k in msg for k in ("timeout", "timed out", "deadline")):
        return AIError("The AI took too long to respond. Try again, or switch to Demo Mode.")
    if any(k in msg for k in ("429", "quota", "rate limit", "resource_exhausted")):
        return AIError("The AI rate limit was reached. Wait a moment and retry, or use Demo Mode.")
    if any(k in msg for k in ("connect", "network", "resolve", "unreachable", "name or service")):
        return AIError("Could not reach the AI service. Check your internet connection or use Demo Mode.")
    return AIError("The AI service returned an error. Try again, or switch to Demo Mode.")


class GeminiProvider:
    is_demo = False

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise AIError("No API key found. Add GEMINI_API_KEY to .env (see .env.example) or use Demo Mode.")
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise AIError("The 'google-genai' package is missing. Run: pip install -r requirements.txt") from None
        self.types = types
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        timeout_ms = int(float(os.getenv("AI_TIMEOUT_SECONDS", "45")) * 1000)
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
        self.name = f"Gemini ({self.model})"

    def _call(self, parts, system: str | None, json_mode: bool = True) -> str:
        try:
            cfg = self.types.GenerateContentConfig(
                system_instruction=system, temperature=0.2,
                response_mime_type="application/json" if json_mode else None)
            return self.client.models.generate_content(model=self.model, contents=parts, config=cfg).text or ""
        except Exception as e:  # noqa: BLE001 - mapped to a friendly message
            raise classify_error(e) from None

    def _img(self, png: bytes):
        return self.types.Part.from_bytes(data=png, mime_type="image/png")

    def analyze(self, transcript, image, context, level, attempt=0) -> dict:
        text = (f"EXPLANATION LEVEL: {level}\n\nSESSION CONTEXT:\n{context}\n\nUSER SAID: {transcript}\n\n"
                + ("An image of the user's screen/camera is attached." if image
                   else "No image attached: rely on speech only and lower your confidence.")
                + "\nReturn the JSON object.")
        raw = self._call(([self._img(image)] if image else []) + [text], SYSTEM_PROMPT)
        data = parse_json_response(raw)
        return normalize_analysis(data) if data else fallback_analysis(raw)

    def verify(self, image, prior, context) -> dict:
        text = (f"PREVIOUS DIAGNOSIS: {json.dumps({k: prior.get(k) for k in ('issue', 'location', 'suggested_fix', 'verification_plan')})}\n"
                f"CONTEXT:\n{context}\nThe attached image is the user's screen AFTER trying the fix.")
        data = parse_json_response(self._call([self._img(image), text], VERIFY_PROMPT)) or {}
        status = data.get("status") if data.get("status") in ("resolved", "still_present", "unclear") else "unclear"
        return {"status": status, "evidence": _s(data.get("evidence")), "remaining_issue": _s(data.get("remaining_issue"))}

    def transcribe(self, audio: bytes, mime: str = "audio/wav") -> str:
        part = self.types.Part.from_bytes(data=audio, mime_type=mime)
        return self._call([part, "Transcribe this speech verbatim. Return only the transcript. Return nothing if there is no speech."],
                          None, json_mode=False).strip()


class DemoProvider:
    """Scripted provider. Labelled as Demo Mode everywhere; not an AI."""
    is_demo = True
    name = "Demo Mode (scripted)"

    def __init__(self, scenario: str = "debug", fail_first: bool = False):
        self.scenario, self.fail_first = scenario, fail_first

    def analyze(self, transcript, image, context, level, attempt=0) -> dict:
        return normalize_analysis(demo_data.get_analysis(self.scenario, attempt, self.fail_first, level))

    def verify(self, image, prior, context) -> dict:
        return {"status": "resolved", "evidence": "Simulated check (Demo Mode)", "remaining_issue": ""}

    def transcribe(self, audio, mime="audio/wav") -> str:
        raise AIError("Voice transcription needs Live AI mode. In Demo Mode use the sample request or type.")
