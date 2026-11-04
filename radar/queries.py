"""Tomorrow's search phrases, written from the names today's run found.

The radar can only see what it searched for, so the word list has to grow by itself: every run
reads the names it just named, works out what kinds of trick they are, and writes new phrases to
search tomorrow. Seeds run every day; generated phrases take turns, least recently used first.
"""
from __future__ import annotations

import json
import re

from . import aisa

SEED = "seed"
GROWN = "generated"
WORDS = re.compile(r"^[a-z0-9 ]+$")

SYSTEM = """You write tomorrow's search phrases for a radar that hunts short-video effects.

It searches TikTok for a phrase like "ai dance filter", reads the videos, and names the effect each
video is about. Today's run named: see "found today". Work out what kinds of trick these are, then
write phrases that would find effects of the same kinds that nobody has named yet.

Rules:
- 2 to 4 lowercase english words, something a person types into TikTok search.
- A phrase is a place to look, never a thing already found: "ai pet filter" is a place to look,
  "jeremy clarkson filter" is one video that already went by.
- Name a subject or an occasion, not an editing technique: "ai wedding photo", "ai baby dance",
  "ai dog filter" are places to look; "color grading", "cinematic mood", "glitch effect", "cartoon
  animation" are what professional editors do, not what an ordinary person searches for.
- Never repeat a phrase in "already tried", and never merely respell a name in "found today".
- No tutorials ("how to"), no brands ("capcut", "tiktok"), no "video".
- Answer with a JSON array of strings and nothing else."""


def ensure(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS queries(word TEXT PRIMARY KEY, source TEXT NOT NULL,"
                 " added TEXT NOT NULL DEFAULT '', runs INTEGER NOT NULL DEFAULT 0,"
                 " last TEXT NOT NULL DEFAULT '')")


def clean(word: str) -> str:
    return " ".join(str(word).lower().split())


def add(conn, words, source: str, day: str) -> list[str]:
    """The words that were new. A word is only ever kept once, seeds included."""
    ensure(conn)
    out = []
    for word in words:
        word = clean(word)
        if not word:
            continue
        cur = conn.execute("INSERT OR IGNORE INTO queries(word, source, added) VALUES (?, ?, ?)",
                           (word, source, day))
        if cur.rowcount:
            out.append(word)
    return out


def tried(conn) -> set[str]:
    ensure(conn)
    return {row["word"] for row in conn.execute("SELECT word FROM queries")}


def due(conn, seeds, limit: int, day: str = "") -> list[str]:
    """Today's words: every seed, then generated ones that ran longest ago."""
    ensure(conn)
    out: list[str] = []
    for seed in seeds:
        seed = clean(seed)
        if seed and seed not in out:
            out.append(seed)
    for row in conn.execute("SELECT word FROM queries WHERE source = ?"
                            " ORDER BY last, runs, rowid", (GROWN,)):  # first in, first out:
        # otherwise the alphabet decides which of sixty words ever runs.
        if len(out) >= limit:
            break
        if row["word"] not in out:
            out.append(row["word"])
    return out[:limit]


def done(conn, words, day: str) -> None:
    ensure(conn)
    for word in words:
        conn.execute("UPDATE queries SET runs = runs + 1, last = ? WHERE word = ?",
                     (day, clean(word)))


def usable(word: str, names: set[str], tried_words: set[str]) -> bool:
    word = clean(word)
    if not 2 <= len(word.split()) <= 4 or not 8 <= len(word) <= 40:
        return False
    if not WORDS.match(word) or word in names or word in tried_words:
        return False
    return not ("how to" in word or "tutorial" in word or "capcut" in word or "tiktok" in word)


def plan(names, tried_words, model: str, want: int = 10) -> tuple[list[str], int]:
    """New phrases to search tomorrow, and the number of calls it took."""
    payload = json.dumps({"found today": sorted(names), "already tried": sorted(tried_words),
                          "want": want}, ensure_ascii=False)
    answer = aisa.chat(model, SYSTEM, payload, max_tokens=600)
    left, right = answer.find("["), answer.rfind("]")
    try:
        rows = json.loads(answer[left:right + 1])
    except ValueError:
        rows = []
    found = {clean(n) for n in names}
    seen = set(tried_words)
    out: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        word = clean(row.get("query") or row.get("phrase") or "") if isinstance(row, dict) else clean(row)
        if word and usable(word, found, seen):
            seen.add(word)
            out.append(word)
    return out[:want], 1
