"""Gate 3: is the slot already taken?

Two checks that cost almost nothing and answer the same question from two sides: how many
pages Google holds with the effect in their title, and whether the obvious domain still exists
on .com, .ai or .io (the .com also gives the registration day, which dates the squat).

Calibration (2026-10-30, month window): `ai photo shoot` 10, `toc toc ai dance` 68,
`thriller ai dance` 76, `hotel lobby ai` 1980 — the last one is a settled topic, not a window.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from . import dotcom, goanyapi

INTITLE_MAX = 20
TLDS = ("com", "ai", "io")


def intitle(term: str) -> tuple[int | None, int]:
    """Pages with the term in the title this month; cost in micro-USD. None when unknown."""
    return goanyapi.intitle(term, "m")


def slug(term: str) -> str:
    """What a site for this effect is actually registered as: no spaces, no punctuation."""
    return "".join(ch for ch in term.lower() if ch.isalnum())[:63]


DOH = "https://cloudflare-dns.com/dns-query"


def _doh(url: str) -> dict:
    """One DNS answer over HTTPS. Over HTTPS because a laptop's resolver lies.

    This machine, like many with a proxy client, answers every name with a 198.18.x.x
    fake address, so socket.getaddrinfo says "taken" for domains that were never registered.
    """
    req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.loads(response.read())


def resolves(host: str) -> bool | None:
    """True when the name exists. None when the lookup itself failed."""
    try:
        answer = _doh(f"{DOH}?{urllib.parse.urlencode({'name': host, 'type': 'A'})}")
    except (OSError, ValueError):
        return None
    status = answer.get("Status")
    if status == 0:
        return True
    if status == 3:
        return False
    return None


def domain(term: str) -> tuple[str, str, str, int]:
    """('free' | 'taken' | 'unknown', registration day, tld that is taken, cost in micro-USD).

    The .com is where a month of registration date comes from; the other endings are only
    asked whether they exist, which is free and catches the squatter who took name.ai.
    """
    base = slug(term)
    if not base:
        return "unknown", "", "", 0
    try:
        row = dotcom.lookup(f"{base}.com")
    except (RuntimeError, OSError):
        row = {}
    hits, unknown = [], False
    if row.get("taken"):
        hits.append("com")
    for tld in TLDS:
        if tld == "com" and row.get("taken"):
            continue
        got = resolves(f"{base}.{tld}")
        if got:
            hits.append(tld)
        elif got is None:
            unknown = True
    if hits:
        return "taken", (row.get("registered") or ""), hits[0], 0
    return ("unknown" if unknown and not row else "free"), "", "", 0


def check(term: str) -> dict:
    pages, paid = intitle(term)
    if pages is not None and 10 <= pages <= 200:      # near the line, where one bad reading decides it
        again, more = intitle(term)
        paid += more
        if again is None or (pages and again and (again / pages > 5 or pages / again > 5)):
            pages = None                              # 46 today, 22500 yesterday: the instrument lies

    state, day, tld, free = domain(term)
    verdict = "pass"
    if pages is None:
        verdict = "unknown"
    elif pages > INTITLE_MAX:
        verdict = "busy"
    elif state == "taken":
        verdict = "claimed"
    return {"intitle": pages, "domain": state, "tld": tld, "registered": day,
            "verdict": verdict, "cost_micro": paid + free}
