"""Agent state machine: understand -> diagnose -> plan -> approve -> act -> verify -> resolve / re-analyse."""
from __future__ import annotations

import re
import time
from typing import Callable

from . import safety, verification
from .ai_engine import AIError
from .memory import SessionMemory

STATE_META = {
    "READY": ("READY", "#34d399", "Waiting for your voice and screen context"),
    "LISTENING": ("LISTENING", "#38bdf8", "Capturing your request"),
    "ANALYZING": ("ANALYZING", "#818cf8", "Reading your request and the visual context"),
    "PLANNING": ("PLANNING", "#a78bfa", "Building an action plan"),
    "WAITING_FOR_APPROVAL": ("WAITING FOR APPROVAL", "#fbbf24", "Nothing changes until you approve"),
    "ACTING": ("ACTING", "#fb923c", "Applying the approved action safely"),
    "VERIFYING": ("VERIFYING", "#22d3ee", "Checking whether the problem is actually solved"),
    "RESOLVED": ("RESOLVED", "#34d399", "Goal verified"),
    "RE_ANALYZING": ("RE-ANALYZING", "#f472b6", "The issue is still present; building a revised plan"),
    "ERROR": ("ERROR", "#f87171", "Something went wrong"),
}
FOLLOWUP_RE = re.compile(r"\b(i did that|did that|i did it|done|what next|what now|next step)\b", re.I)


class Agent:
    def __init__(self, provider=None, notify: Callable | None = None, pace: float = 0.5):
        self.provider, self.notify, self.pace = provider, notify, pace
        self.reset()

    # ------------------------------------------------------------ plumbing
    def reset(self) -> None:
        self.memory = SessionMemory()
        self.state, self.state_detail = "READY", ""
        self.analysis: dict | None = None
        self.action: safety.ActionRequest | None = None
        self.verification: dict | None = None
        self.error: str | None = None
        self.awaiting_user = False
        self.attempt = 0
        self.level = "Beginner"
        self.last_image: bytes | None = None
        self.risk_flags: list[str] = []

    def _set(self, state: str, detail: str = "") -> None:
        self.state, self.state_detail = state, detail
        if self.notify:
            try:
                self.notify(self)
            except Exception:  # UI refresh must never break the agent
                pass

    def _pause(self) -> None:
        if self.provider is not None and self.provider.is_demo and self.pace:
            time.sleep(self.pace)

    def _fail(self, msg: str) -> bool:
        self.error = msg
        self.memory.log("Error", msg, "err")
        self._set("ERROR", msg)
        return False

    def _resolve(self, label: str = "Task resolved") -> None:
        self.memory.resolved_at = time.time()
        self.memory.log(label, "", "ok")
        self._set("RESOLVED", "Goal verified" if self.verification else "Explanation delivered")

    # ------------------------------------------------------------ main entry
    def submit(self, transcript: str, image: bytes | None, level: str = "Beginner", source: str = "text") -> bool:
        transcript = (transcript or "").strip()
        self.error, self.level, self.last_image = None, level, image
        if not transcript:
            return self._fail("Say or type what you need help with first.")
        if self.provider is None:
            return self._fail("No AI provider is available. Add an API key or switch to Demo Mode.")
        m = self.memory
        m.started_at = m.started_at or time.time()
        m.add_turn("user", transcript)
        m.log("Voice captured" if source == "voice" else "Request received", transcript[:90], "ok")
        if self.analysis and self.provider.is_demo and FOLLOWUP_RE.search(transcript):
            return self._demo_followup()
        self._set("ANALYZING")
        try:
            result = self.provider.analyze(transcript, image, m.context_text(), level, attempt=self.attempt)
        except AIError as e:
            return self._fail(e.user_message)
        except Exception:
            return self._fail("Unexpected problem while analysing. Please try again or use Demo Mode.")
        return self._accept(result)

    def _demo_followup(self) -> bool:
        replies = {
            "WAITING_FOR_APPROVAL": "Nothing has been changed yet. Approve the proposed fix when you're ready.",
            "RESOLVED": "The goal is already verified as completed. Clear the session to start a new task.",
        }
        text = replies.get(self.state, "Noted. Continue with the current plan. (Demo Mode scripted reply)")
        self.memory.add_turn("assistant", text)
        self.memory.log("Follow-up answered (demo)", text, "info")
        self._set(self.state, self.state_detail)
        return True

    def _build_action(self, a: dict) -> safety.ActionRequest:
        raw = a.get("action") if a.get("demo") else None  # only trusted for scripted demo content
        if isinstance(raw, dict):
            return safety.ActionRequest(**{k: v for k, v in raw.items() if k in safety.ActionRequest.__dataclass_fields__})
        return safety.ActionRequest("guide_user", "user", a["issue"], a["suggested_fix"])

    def _accept(self, a: dict) -> bool:
        m, self.analysis = self.memory, a
        self._pause()
        if a.get("fallback"):
            m.log("Unstructured reply (fallback)", "Showing plain-text answer", "warn")
            m.add_turn("assistant", a["explanation"])
            self._set("READY", "Answered in plain text")
            return True
        m.goal = a["goal"]
        m.log("Screen analyzed" if self.last_image else "Request analyzed", "", "ok")
        m.log("Goal detected", a["goal"], "ok")
        m.log("Issue identified", a["issue"], "ok")
        self._set("PLANNING")
        self._pause()
        self.risk_flags = safety.scan_risky(" ".join([a["suggested_fix"]] + a["action_plan"]))
        self.action = self._build_action(a)
        m.log("Fix proposed", a["suggested_fix"], "ok")
        plan = " ".join(f"{i}. {s}" for i, s in enumerate(a["action_plan"], 1))
        m.add_turn("assistant", f"Issue: {a['issue']} | Fix: {a['suggested_fix']} | Plan: {plan}")
        if a["action_plan"] and (a["requires_approval"] or self.risk_flags or self.action.kind == "patch_demo_file"):
            m.log("Waiting for approval", "", "warn")
            self._set("WAITING_FOR_APPROVAL")
        else:
            self._resolve("Explanation delivered")
        return True

    # ------------------------------------------------------------ approval
    def approve(self) -> bool:
        if self.state != "WAITING_FOR_APPROVAL" or not self.action:
            return False
        m = self.memory
        m.log("Action approved", self.action.reason, "ok")
        m.add_turn("user", "[Approved the proposed action]")
        ok, msg = safety.validate_action(self.action)
        if not ok:
            return self._fail(msg)
        self._set("ACTING", self.action.reason)
        self._pause()
        if self.action.kind == "patch_demo_file":
            ok, msg = safety.apply_demo_patch(self.action)
            if not ok:
                return self._fail(msg)
            m.log("Safe demo fix applied", msg, "ok")
            return self._verify_workspace()
        if self.provider is not None and self.provider.is_demo:
            m.log("Guided step (simulated)", "Demo Mode: ContextBridge does not click for you", "warn")
            self._set("VERIFYING")
            self._pause()
            self.verification = {"status": "success", "simulated": True,
                                 "detail": "Simulated verification (Demo Mode): the Offline indicator would clear after Retry."}
            m.log("Verification complete (simulated)", "", "ok")
            self._resolve()
            return True
        self.awaiting_user = True
        m.log("Guiding user", "Apply the change yourself, then verify with a new screenshot", "info")
        self._set("ACTING", "Apply the change yourself, then verify with a fresh screenshot")
        return True

    def reject(self) -> None:
        if self.state != "WAITING_FOR_APPROVAL":
            return
        self.memory.log("Action rejected", "No changes were made", "warn")
        self.memory.add_turn("user", "[Rejected the proposed action]")
        self.action, self.awaiting_user = None, False
        self._set("READY", "Plan rejected. Nothing was changed. Tell me what you'd prefer.")

    # ------------------------------------------------------------ verification loop
    def _verify_workspace(self) -> bool:
        self._set("VERIFYING")
        self._pause()
        res = self.verification = verification.verify_demo_workspace("6")
        if res["status"] == "success":
            self.memory.log("Verification complete", res["detail"], "ok")
            self._resolve()
            return True
        self.memory.log("Verification failed", res["detail"], "err")
        return self._reanalyze(res["detail"])

    def verify_live(self, new_image: bytes | None) -> bool:
        """Live mode: verify with a fresh screenshot of the user's screen."""
        if not self.awaiting_user or self.provider is None:
            return False
        if not new_image:
            return self._fail("Upload a new screenshot showing the result so I can verify it.")
        self.error, self.last_image = None, new_image
        self._set("VERIFYING")
        try:
            res = self.provider.verify(new_image, self.analysis, self.memory.context_text())
        except AIError as e:
            return self._fail(e.user_message)
        except Exception:
            return self._fail("Unexpected problem while verifying. Please try again.")
        self.verification = {"status": "success" if res["status"] == "resolved" else "failed",
                             "detail": res["evidence"] or res["remaining_issue"], "simulated": False}
        if res["status"] == "resolved":
            self.awaiting_user = False
            self.memory.log("Verification complete", res["evidence"], "ok")
            self._resolve()
            return True
        if res["status"] == "unclear":
            self.memory.log("Verification unclear", "Need a clearer screenshot", "warn")
            self._set("ACTING", "I can't tell from that image. Upload a clearer screenshot of the result.")
            return True
        self.awaiting_user = False
        self.memory.log("Verification failed", res["remaining_issue"], "err")
        return self._reanalyze(res["remaining_issue"] or res["evidence"])

    def _reanalyze(self, reason: str) -> bool:
        m = self.memory
        m.record_attempt(self.analysis or {}, reason)
        self.attempt += 1
        self._set("RE_ANALYZING")
        m.log("Re-analyzing updated context", reason, "warn")
        try:
            result = self.provider.analyze(f"The previous fix did not work. {reason}", self.last_image,
                                           m.context_text(), self.level, attempt=self.attempt)
        except AIError as e:
            return self._fail(e.user_message)
        except Exception:
            return self._fail("Unexpected problem while re-analysing. Please try again.")
        return self._accept(result)
