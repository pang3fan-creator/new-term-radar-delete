"""Gate 1: is this video showing a thing, and what would a stranger type to get it?

The upstream judge answers "is this a proper noun". This one answers "is this an effect
someone could search for": `toc toc ai dance` passes, `AI is crazy` does not, and neither
does a model version number, because nobody goes looking for one.
"""
from __future__ import annotations

from . import llm

SYSTEM = (
    "Name the THING each TikTok video shows, for a radar that looks for effects ordinary "
    "people want to copy without a studio.\n"
    "Answer with the words a stranger would type into Google to get the same result: 2-4 "
    "lowercase words, no hashtags, no @handles, no creator names. Keep a brand only when the "
    "brand IS the thing.\n"
    "Examples: 'toc toc ai dance', 'thriller ai dance', 'ai baby podcast', 'red light filter'.\n"
    "A tutorial is not an effect: name what it teaches, not \"x tutorial\". A category that "
    "covers a whole genre ('lyric video filter', 'color grading', 'ai dance') is not a name "
    "either.\n"
    "Answer \"none\" when the video shows no repeatable effect: a skit, a reaction, an "
    "opinion, a rant, a product unboxing, a model release, a personal vlog.\n"
    "Answer with JSON only, one row per input: [{\"i\": 0, \"name\": \"toc toc ai dance\"}]"
)


PLATFORMS = {"capcut", "tiktok", "youtube", "instagram", "reels", "snapchat", "canva"}


TAIL = {"meme", "trend", "challenge", "video", "viral"}


def bare(name: str) -> str:
    """'im sorry i lied meme' is what we call it; 'im sorry i lied' is what people type."""
    words = name.split()
    while len(words) > 2 and words[-1] in TAIL:
        words.pop()
    return " ".join(words)


def own_platform(name: str) -> bool:
    """'capcut pioneer template' is a preset inside CapCut: the demand goes to the app, not a site."""
    return bool(PLATFORMS.intersection(name.lower().split()))


def names(posts: list[dict], model: str) -> tuple[dict[int, str], int]:
    """{index in posts: effect name}; videos answered "none" are left out. Returns calls made."""
    items = [{"caption": (p.get("title") or "")[:220],
              "hashtags": [h for h in (p.get("hashtags") or []) if h]} for p in posts]
    got, calls = llm.ask(model, SYSTEM, items, "name", size=25)
    kept = {i: bare(v) for i, v in got.items() if v and v != "none"}
    return {i: v for i, v in kept.items() if not own_platform(v)}, calls
