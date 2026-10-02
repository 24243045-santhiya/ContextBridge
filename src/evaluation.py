"""Evaluation log: record real test cases, then summarise. No numbers are pre-filled."""
from __future__ import annotations

import csv
import io

FIELDS = ["case", "scenario", "time_to_resolution_s", "issue_identified_correctly",
          "recommendation_useful", "verification_succeeded", "notes"]
TARGET_CASES = 20
BASELINE_MINUTES = 12   # target assumption, not a measured result
TARGET_MINUTES = 2      # target, not a measured result


def summarize(records: list[dict]) -> dict | None:
    n = len(records)
    if not n:
        return None
    pct = lambda k: round(100 * sum(1 for r in records if r[k]) / n)
    times = [r["time_to_resolution_s"] for r in records if r["time_to_resolution_s"] is not None]
    return {
        "cases": n,
        "avg_time_s": round(sum(times) / len(times)) if times else None,
        "identified_pct": pct("issue_identified_correctly"),
        "useful_pct": pct("recommendation_useful"),
        "verified_pct": pct("verification_succeeded"),
    }


def to_csv(records: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    for r in records:
        w.writerow({k: r.get(k, "") for k in FIELDS})
    return buf.getvalue()
