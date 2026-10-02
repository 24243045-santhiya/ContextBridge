"""Session memory: conversation turns, agent timeline, goal and failed attempts."""
from __future__ import annotations

import time
from dataclasses import dataclass


def now_str() -> str:
    return time.strftime("%H:%M:%S")


@dataclass
class Turn:
    role: str
    text: str
    ts: str


@dataclass
class TimelineEvent:
    ts: str
    label: str
    detail: str = ""
    kind: str = "info"  # info | ok | warn | err


class SessionMemory:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.turns: list[Turn] = []
        self.timeline: list[TimelineEvent] = []
        self.attempts: list[dict] = []
        self.goal = ""
        self.started_at: float | None = None
        self.resolved_at: float | None = None

    def add_turn(self, role: str, text: str) -> None:
        self.turns.append(Turn(role, text, now_str()))

    def log(self, label: str, detail: str = "", kind: str = "info") -> None:
        self.timeline.append(TimelineEvent(now_str(), label, detail, kind))

    def record_attempt(self, analysis: dict, outcome: str) -> None:
        self.attempts.append({"fix": analysis.get("suggested_fix", ""), "outcome": outcome})

    def context_text(self, max_turns: int = 8) -> str:
        """Compact history handed to the model so 'that' / 'it' can be resolved."""
        lines = []
        if self.goal:
            lines.append(f"Current goal: {self.goal}")
        for i, a in enumerate(self.attempts, 1):
            lines.append(f"Earlier fix attempt {i} did NOT work. Fix: {a['fix']} | Outcome: {a['outcome']}")
        recent = self.turns[-max_turns:]
        if recent:
            lines.append("Conversation so far (oldest first):")
            lines += [f"{t.role.upper()}: {t.text}" for t in recent]
        return "\n".join(lines) if lines else "(new session, no history)"

    def elapsed_seconds(self) -> int | None:
        if self.started_at is None:
            return None
        return int((self.resolved_at or time.time()) - self.started_at)
