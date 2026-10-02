"""Result verification for the sandboxed demo workspace.

Runs ONLY demo_workspace/app.py (never AI-supplied code) with a fixed command,
isolated mode and a timeout, then compares stdout with the expected value.
"""
from __future__ import annotations

import subprocess
import sys

from . import safety


def verify_demo_workspace(expected: str = "6", timeout: int = 5) -> dict:
    path = safety.DEMO_WORKSPACE / "app.py"
    if not path.exists():
        return {"status": "failed", "detail": "Workspace file missing.", "output": "", "simulated": False}
    try:
        p = subprocess.run([sys.executable, "-I", str(path)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(safety.DEMO_WORKSPACE))
    except subprocess.TimeoutExpired:
        return {"status": "failed", "detail": "Program timed out (possible infinite loop).", "output": "", "simulated": False}
    out, err = p.stdout.strip(), p.stderr.strip()
    if p.returncode != 0:
        last = err.splitlines()[-1] if err else "unknown error"
        return {"status": "failed", "detail": f"Program still crashes: {last}", "output": out, "simulated": False}
    if out != expected:
        return {"status": "failed", "detail": f"No crash, but output is '{out}' (expected '{expected}').",
                "output": out, "simulated": False}
    return {"status": "success", "detail": f"Program runs and prints the expected value ({expected}).",
            "output": out, "simulated": False}
