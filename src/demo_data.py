"""Scripted DEMO MODE content + synthetic sample screenshots (generated with Pillow).

Everything here is scripted and always labelled "Demo Mode" in the UI. It is
not the output of an AI model.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "demo"
W, H = 1280, 720

IMAGES = {
    "debug": DEMO_DIR / "sample_screenshot.png",
    "ui": DEMO_DIR / "sample_ui.png",
    "chart": DEMO_DIR / "sample_chart.png",
}

SCENARIOS = {
    "debug": {"title": "1 · Debugging a Python error (primary)", "utterance": "I need to get this program running. Find what's wrong and guide me."},
    "ui": {"title": "2 · App / UI problem", "utterance": "What should I do here?"},
    "chart": {"title": "3 · Document / chart", "utterance": "Explain what I'm looking at."},
}


# ---------------------------------------------------------------- drawing
def _font(size, kind="mono"):
    paths = {
        "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "C:/Windows/Fonts/consola.ttf", "/System/Library/Fonts/Menlo.ttc"],
        "sans": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Helvetica.ttc"],
    }[kind]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _make_debug() -> Image.Image:
    img = Image.new("RGB", (W, H), "#1e1e2e")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 44], fill="#181825")
    d.text((24, 11), "app.py  —  demo_project", font=_font(20, "sans"), fill="#a6adc8")
    code = open(DEMO_DIR / "sample_error.py", encoding="utf-8").read().splitlines()
    kw = {"def", "while", "return"}
    f = _font(24)
    for i, line in enumerate(code):
        y = 70 + i * 36
        d.text((24, y), str(i + 1), font=f, fill="#585b70")
        x = 70
        for tok in re.findall(r"\s+|\w+|[^\w\s]", line):
            col = "#cba6f7" if tok in kw else "#89b4fa" if tok == "print" else "#fab387" if tok.isdigit() else "#cdd6f4"
            d.text((x, y), tok, font=f, fill=col)
            x += f.getlength(tok)
    d.rectangle([0, 400, W, H], fill="#11111b")
    d.text((24, 412), "TERMINAL", font=_font(18, "sans"), fill="#7f849c")
    tb = ['Traceback (most recent call last):', '  File "app.py", line 8, in <module>', '    print(digit_sum(123))',
          '  File "app.py", line 4, in digit_sum', '    total += remainder', "NameError: name 'remainder' is not defined"]
    for i, t in enumerate(tb):
        d.text((24, 450 + i * 36), t, font=f, fill="#f38ba8" if i == len(tb) - 1 else "#bac2de")
    return img


def _make_ui() -> Image.Image:
    img = Image.new("RGB", (W, H), "#e9edf3")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 60], fill="#ffffff")
    d.text((30, 16), "Acme Notes", font=_font(26, "sans"), fill="#1f2937")
    d.rounded_rectangle([1090, 16, 1250, 46], 15, fill="#fee2e2")
    d.text((1112, 20), "● Offline", font=_font(20, "sans"), fill="#b91c1c")
    d.rounded_rectangle([240, 200, 1040, 440], 14, fill="#ffffff", outline="#fca5a5", width=3)
    d.text((280, 230), "Sync failed", font=_font(34, "sans"), fill="#991b1b")
    d.text((280, 285), "Could not reach server (ERR_CONNECTION_REFUSED).", font=_font(24, "sans"), fill="#374151")
    d.rounded_rectangle([280, 350, 420, 400], 8, fill="#2563eb")
    d.text((322, 362), "Retry", font=_font(24, "sans"), fill="#ffffff")
    d.rounded_rectangle([440, 350, 760, 400], 8, outline="#9ca3af", width=2, fill="#ffffff")
    d.text((466, 362), "Open Network Settings", font=_font(22, "sans"), fill="#374151")
    return img


CHART_VALUES = [("Jan", 12), ("Feb", 15), ("Mar", 19), ("Apr", 14), ("May", 22), ("Jun", 27)]


def _make_chart() -> Image.Image:
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)
    d.text((140, 36), "Monthly active users (thousands)", font=_font(32, "sans"), fill="#111827")
    for g in range(0, 30, 5):
        y = 620 - g * 18
        d.line([120, y, 1160, y], fill="#e5e7eb", width=1)
        d.text((80, y - 10), str(g), font=_font(18, "sans"), fill="#6b7280")
    for i, (m, v) in enumerate(CHART_VALUES):
        x = 140 + i * 166
        d.rectangle([x, 620 - v * 18, x + 100, 620], fill="#6366f1" if m != "Apr" else "#f59e0b")
        d.text((x + 28, 628), m, font=_font(22, "sans"), fill="#374151")
        d.text((x + 30, 620 - v * 18 - 30), f"{v}K", font=_font(22, "sans"), fill="#111827")
    return img


def ensure_demo_assets(force: bool = False) -> None:
    makers = {"debug": _make_debug, "ui": _make_ui, "chart": _make_chart}
    for key, path in IMAGES.items():
        if force or not path.exists():
            makers[key]().save(path)


# ---------------------------------------------------------------- scripted analyses
def _box(x, y, w, h):
    return [round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4)]


_GOOD = {
    "goal": "Get the Python program running (resolve the visible NameError)",
    "issue": "NameError: variable 'remainder' is used before it is assigned",
    "location": "app.py, line 4: `total += remainder` inside digit_sum()",
    "cause": "'remainder' is never given a value before the loop body reads it.",
    "explanations": {
        "Beginner": "The program tries to use a value called 'remainder', but nobody ever created it. It's like adding a number from a box that was never filled. The last digit of the number should be put in that box first.",
        "Intermediate": "'remainder' is read on line 4 but never assigned in the function scope, so Python raises NameError. The loop is meant to peel off the last digit each pass, so remainder should be num % 10.",
        "Expert": "Unbound name `remainder` in digit_sum (line 4). Missing `remainder = num % 10` before accumulation.",
    },
    "suggested_fix": "Calculate the remainder with `remainder = num % 10` before adding it to `total`.",
    "action_plan": ["Add `remainder = num % 10` before `total += remainder`.",
                    "Re-run the program in the sandbox.",
                    "Verify that digit_sum(123) prints 6 with no error."],
    "confidence": "High: the traceback and the offending line are both visible",
    "requires_approval": True,
    "verification_plan": "Run demo_workspace/app.py in isolated mode and check that it prints 6.",
    "highlight": _box(60, 168, 640, 44),
    "spoken_summary": "The variable remainder is used on line 4 before it is created. I suggest setting remainder to num modulo 10 first. Do you want me to apply that fix in the demo workspace?",
    "action": {"kind": "patch_demo_file", "target": "app.py", "reason": "Fix undefined variable 'remainder'",
               "find": "        total += remainder\n", "replace": "        remainder = num % 10\n        total += remainder\n",
               "proposed_change": "+        remainder = num % 10\n         total += remainder"},
}

_PARTIAL = copy.deepcopy(_GOOD)
_PARTIAL.update({
    "suggested_fix": "Initialise `remainder = 0` before the loop so the name exists.",
    "action_plan": ["Add `remainder = 0` after `total = 0`.", "Re-run the program in the sandbox.", "Verify the error is gone."],
    "confidence": "Medium: this removes the crash, but the intended logic is not shown on screen",
    "spoken_summary": "The variable remainder is never defined. I suggest initialising it to zero before the loop. Shall I apply that?",
    "action": {"kind": "patch_demo_file", "target": "app.py", "reason": "Define 'remainder' before use",
               "find": "    total = 0\n", "replace": "    total = 0\n    remainder = 0\n",
               "proposed_change": "     total = 0\n+    remainder = 0"},
})

_RETRY = copy.deepcopy(_GOOD)
_RETRY.update({
    "issue": "The crash is gone, but the result is wrong: 'remainder' is always 0",
    "cause": "The first fix only created the variable. It never takes the last digit of num, so every pass adds 0.",
    "spoken_summary": "That fix removed the crash but the output is wrong, because remainder is always zero. It should be set to num modulo 10 inside the loop. Shall I apply the corrected change?",
})
_RETRY["explanations"] = {k: "Re-analysis: " + v for k, v in {
    "Beginner": "The box now exists but it holds 0 forever, so nothing gets added. We need to put the last digit of the number in the box on every pass.",
    "Intermediate": "The name is defined, but `remainder` is never updated inside the loop, so total stays 0. Assign remainder = num % 10 each iteration.",
    "Expert": "`remainder` is initialised but loop-invariant (0). Recompute `num % 10` per iteration.",
}.items()}

_UI = {
    "goal": "Get the app syncing again",
    "issue": "The app is offline: sync failed with ERR_CONNECTION_REFUSED",
    "location": "Red 'Sync failed' dialog in the centre and the 'Offline' indicator at the top right",
    "cause": "The app cannot reach its server. Common reasons are no network, a VPN/proxy problem or a server outage. The screenshot cannot tell which one it is.",
    "explanations": {
        "Beginner": "The app says it can't connect to the internet or to its server, so your notes aren't saving. First check that you're online, then press Retry.",
        "Intermediate": "ERR_CONNECTION_REFUSED means the connection attempt was actively refused or nothing is listening. Check network/VPN/proxy, then retry.",
        "Expert": "Connection refused on sync endpoint; client shows Offline. Verify connectivity/VPN/proxy before retrying; server-side outage not excluded.",
    },
    "suggested_fix": "Confirm your device is online (or reconnect the VPN), then click Retry. If it fails again, open Network Settings.",
    "action_plan": ["Confirm your internet / VPN connection is working.", "Click Retry in the dialog.", "Check that the indicator changes from Offline to Online."],
    "confidence": "Medium: the error text is clear, the root cause is not visible",
    "requires_approval": True,
    "verification_plan": "Look for the Offline indicator to disappear after Retry.",
    "highlight": _box(240, 200, 800, 240),
    "spoken_summary": "The app can't reach its server, so sync failed. Check your connection, then press Retry. I can't tell from the screenshot whether it's your network or the server.",
    "action": {"kind": "guide_user", "target": "user", "reason": "Guide the user to retry the sync",
               "proposed_change": "You click Retry after confirming your connection (ContextBridge does not click for you)."},
}

_CHART = {
    "goal": "Understand what the chart shows",
    "issue": "Nothing is broken. This is an explanation request",
    "location": "Whole chart; the highlighted April bar is the one dip",
    "cause": "Active users rise from 12K in January to 27K in June, with a drop to 14K in April.",
    "explanations": {
        "Beginner": "This chart counts how many people used the product each month. It mostly goes up, from 12 thousand in January to 27 thousand in June. April is the one month it dipped.",
        "Intermediate": "Monthly active users grow from 12K to 27K (about 2.25x) over six months, with a one-month decline in April (19K to 14K) before a strong recovery.",
        "Expert": "MAU 12K to 27K Jan to Jun, April dip (-26% MoM from 19K to 14K), May/Jun rebound (+57%, +23%). Cause of the dip is not shown.",
    },
    "suggested_fix": "No action needed. If useful, investigate what changed in April (release, outage, campaign end).",
    "action_plan": [],
    "confidence": "High for the labelled values; the reason for the dip is not visible",
    "requires_approval": False,
    "verification_plan": "",
    "highlight": _box(620, 330, 136, 282),
    "spoken_summary": "This chart shows monthly active users growing from twelve thousand in January to twenty-seven thousand in June, with a dip in April. The chart doesn't say why April dropped.",
    "action": None,
}


def analysis_sequence(scenario: str, fail_first: bool = False) -> list[dict]:
    if scenario == "ui":
        return [_UI]
    if scenario == "chart":
        return [_CHART]
    return [_PARTIAL, _RETRY] if fail_first else [_GOOD]


def get_analysis(scenario: str, attempt: int, fail_first: bool, level: str) -> dict:
    seq = analysis_sequence(scenario, fail_first)
    a = copy.deepcopy(seq[min(attempt, len(seq) - 1)])
    a["explanation"] = a["explanations"].get(level) or a["explanations"]["Beginner"]
    a["demo"] = True
    return a
