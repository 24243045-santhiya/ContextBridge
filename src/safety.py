"""Safety layer. ContextBridge never runs AI-generated commands.

The only action that touches a file is an allow-listed find/replace patch on
`demo_workspace/app.py`, a sandbox copy of demo/sample_error.py. Everything
else is *guidance* that the human performs.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_WORKSPACE = ROOT / "demo_workspace"
TEMPLATE = ROOT / "demo" / "sample_error.py"
ALLOWED_KINDS = {"patch_demo_file", "guide_user"}
ALLOWED_FILES = {"app.py"}

RISKY_PATTERNS = [
    r"rm\s+-[a-z]*r", r"\bsudo\b", r"curl[^|\n]*\|\s*(ba|z)?sh", r"\bpip3?\s+install\b",
    r"\bnpm\s+install\b", r"\bdel\s+/", r"\bformat\s+[a-z]:", r"\bmkfs\b", r"shutil\.rmtree",
    r"os\.system", r"subprocess", r"drop\s+table", r"chmod\s+-r", r"git\s+push\s+--force",
    r"\beval\(", r"\bexec\(",
]


@dataclass
class ActionRequest:
    kind: str
    target: str
    reason: str
    proposed_change: str = ""
    find: str = ""
    replace: str = ""
    reversible: bool = True


def scan_risky(text: str) -> list[str]:
    """Return the risky patterns found in AI text (we warn and never execute them)."""
    return [p for p in RISKY_PATTERNS if re.search(p, text or "", re.I)]


def validate_action(a: ActionRequest) -> tuple[bool, str]:
    if a.kind not in ALLOWED_KINDS:
        return False, f"Blocked: action type '{a.kind}' is not allowed."
    if a.kind == "patch_demo_file":
        if a.target not in ALLOWED_FILES:
            return False, "Blocked: only files inside the demo workspace can be modified."
        path = (DEMO_WORKSPACE / a.target).resolve()
        if DEMO_WORKSPACE.resolve() not in path.parents:
            return False, "Blocked: path escapes the demo workspace."
        if scan_risky(a.replace):
            return False, "Blocked: the proposed change contains a risky pattern."
    return True, "ok"


def reset_workspace() -> None:
    DEMO_WORKSPACE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, DEMO_WORKSPACE / "app.py")


def read_workspace_file() -> str:
    p = DEMO_WORKSPACE / "app.py"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def apply_demo_patch(a: ActionRequest) -> tuple[bool, str]:
    ok, msg = validate_action(a)
    if not ok:
        return False, msg
    path = DEMO_WORKSPACE / a.target
    if not path.exists():
        reset_workspace()
    src = path.read_text(encoding="utf-8")
    if src.count(a.find) != 1:
        return False, "Patch target not found exactly once; nothing was changed."
    path.write_text(src.replace(a.find, a.replace), encoding="utf-8")
    return True, f"Patched demo_workspace/{a.target}"
