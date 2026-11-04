"""Does anyone search this phrase, and is that number going up?

Gate 4, and the only one that costs money per would-be answer: it runs only when the other three
would ship. It reads a year of weekly points, not a quarter of daily ones — daily series round small
phrases to zero, and a zero there means "below the sampling threshold", not "nobody searches".

A window changes the answer: "ai dance filter" reads 27/100 over 28 days against 31/100 for the
quarter before it (flat), while the same phrase over three months of daily points reads zero.
"""
from __future__ import annotations

import statistics

from . import goanyapi

WINDOW = "today 12-m"   # weekly points: a real number instead of a rounded zero
COST_MICRO = 6_000
RISING = 1.2            # the last four weeks against the thirteen before them
FLOOR = 5.0             # below this a ratio is noise, not demand
FADING = 0.5            # of its own peak
STALE = 30              # days after the peak that a fading curve counts as closed


def series(term: str, geo: str = "US"):
    return goanyapi.daily_series(term, geo, WINDOW)


def judge(points) -> dict:
    """rising / flat / falling / silent, from a (date, value) weekly series."""
    values = [value for _, value in points]
    if not values or max(values) == 0:
        return {"verdict": "silent", "now": 0.0, "peak": 0, "peak_day": "", "ratio": 0.0}
    now = round(statistics.mean(values[-4:]), 1)
    before = round(statistics.mean(values[-17:-4]), 1) if len(values) >= 17 else now
    peak_day, peak = max(points, key=lambda point: point[1])
    ratio = round(now / before, 2) if before else 0.0
    if now >= FLOOR and ratio >= RISING:
        verdict = "rising"
    elif now < peak * FADING and (points[-1][0] - peak_day).days > STALE:
        verdict = "falling"
    else:
        verdict = "flat"
    return {"verdict": verdict, "now": now, "peak": peak, "peak_day": str(peak_day), "ratio": ratio}


def check(term: str) -> dict:
    points, micro = series(term)
    out = judge(points)
    out["value"] = f"{out['now']}/{out['peak']}"
    out["cost_micro"] = micro
    return out
