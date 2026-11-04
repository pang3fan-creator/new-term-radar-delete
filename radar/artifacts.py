"""Memory for the fork: effects, the sightings that saw them, and the checks spent on them.

The upstream radar stores names in one row per term (store.py). This one stores the thing,
every place it was seen, and every answer bought about it, because the same effect shows up
as many videos and each check costs money.

observe()   one sighting; creates the effect on first sight, never twice for the same URL.
gate()      one gate result (want / intitle / domain), with its cost in micro-dollars.
top()       the effects worth spending money on today, by peak views.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  key        TEXT,
  kind       TEXT NOT NULL DEFAULT 'effect',
  first_seen TEXT NOT NULL,
  last_seen  TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS observations (
  id          INTEGER PRIMARY KEY,
  artifact_id INTEGER NOT NULL REFERENCES artifacts(id),
  platform    TEXT NOT NULL,
  url         TEXT NOT NULL UNIQUE,
  author      TEXT NOT NULL DEFAULT '',
  caption     TEXT NOT NULL DEFAULT '',
  views       INTEGER NOT NULL DEFAULT 0,
  comments    INTEGER NOT NULL DEFAULT 0,
  uploaded_at TEXT NOT NULL DEFAULT '',
  seen_at     TEXT NOT NULL DEFAULT '',
  promo       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS observations_artifact ON observations(artifact_id);
CREATE TABLE IF NOT EXISTS runs (
  id          INTEGER PRIMARY KEY,
  day         TEXT NOT NULL,
  at          TEXT NOT NULL DEFAULT '',
  words       TEXT NOT NULL DEFAULT '',   -- what it searched for
  discovered  INTEGER NOT NULL DEFAULT 0,
  posts       INTEGER NOT NULL DEFAULT 0, -- fresh enough to name
  named       INTEGER NOT NULL DEFAULT 0,
  candidates  INTEGER NOT NULL DEFAULT 0, -- made it into the report
  grown       TEXT NOT NULL DEFAULT '',   -- what it added for tomorrow
  cost_micro  INTEGER NOT NULL DEFAULT 0,
  opens       INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checks (
  id          INTEGER PRIMARY KEY,
  artifact_id INTEGER NOT NULL REFERENCES artifacts(id),
  gate        TEXT NOT NULL,
  value       TEXT NOT NULL,
  verdict     TEXT NOT NULL,
  cost_micro  INTEGER NOT NULL DEFAULT 0,
  at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS checks_artifact ON checks(artifact_id)
"""


MODIFIERS = frozenset({"ai", "capcut", "filter", "effect", "trend", "template", "video",
                       "face", "tutorial"})


def normalize(name: str) -> str:
    return " ".join(name.lower().split())


def key(name: str) -> str:
    """Identity, not display. `jeremy clarkson ai filter`, `... capcut filter` and `... ai face
    filter` are one thing seen three times: the modifier drifts between runs, the content words
    do not. Sorted, so word order drift does not matter either."""
    words = normalize(name).split()
    content = [w for w in words if w not in MODIFIERS]
    return " ".join(sorted(content or words))


def connect(state_dir: Path) -> sqlite3.Connection:
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(state_dir / "radar.db", isolation_level=None)  # write-through
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Add `key` to a database written before effects had an identity, merging what it splits.

    Existing rows carry the drift: `jeremy clarkson filter` and `jeremy clarkson capcut filter`
    are two artifacts for one thing. Keeping the oldest row and moving the sightings onto it is
    the only merge that does not invent information.
    """
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(artifacts)")}
    if "key" not in columns:
        conn.execute("ALTER TABLE artifacts ADD COLUMN key TEXT")
    for row in conn.execute("SELECT id, name, key FROM artifacts").fetchall():
        if not row["key"]:
            conn.execute("UPDATE artifacts SET key = ? WHERE id = ?", (key(row["name"]), row["id"]))
    groups = conn.execute("SELECT key, MIN(id) AS keep, COUNT(*) AS n FROM artifacts"
                          " GROUP BY key HAVING n > 1").fetchall()
    for group in groups:
        losers = [r["id"] for r in conn.execute(
            "SELECT id FROM artifacts WHERE key = ? AND id != ?", (group["key"], group["keep"]))]
        for old in losers:
            # A sighting or a check that already exists on the keeper is a duplicate, not a loss.
            conn.execute("UPDATE OR IGNORE observations SET artifact_id = ? WHERE artifact_id = ?",
                         (group["keep"], old))
            conn.execute("DELETE FROM observations WHERE artifact_id = ?", (old,))
            conn.execute("UPDATE checks SET artifact_id = ? WHERE artifact_id = ?", (group["keep"], old))
            conn.execute("DELETE FROM artifacts WHERE id = ?", (old,))
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS artifacts_key ON artifacts(key)")


def observe(conn: sqlite3.Connection, name: str, *, platform: str, url: str,
            author: str = "", caption: str = "", views: int = 0, comments: int = 0,
            uploaded_at: str = "", seen_at: str = "", promo: int = 0) -> int:
    """Record one sighting and return the effect's id.

    The first name wins as the display name: renaming on every run would make the same effect
    look new each time.
    """
    now = seen_at or uploaded_at
    conn.execute(
        "INSERT INTO artifacts (name, key, first_seen, last_seen) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(key) DO UPDATE SET"
        "   first_seen = MIN(first_seen, excluded.first_seen),"
        "   last_seen  = MAX(last_seen, excluded.last_seen)",
        (normalize(name), key(name), now, now),
    )
    artifact_id = conn.execute("SELECT id FROM artifacts WHERE key = ?", (key(name),)).fetchone()[0]
    conn.execute(
        "INSERT INTO observations (artifact_id, platform, url, author, caption, views,"
        " comments, uploaded_at, seen_at, promo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(url) DO UPDATE SET"
        "   views = MAX(views, excluded.views),"
        "   comments = MAX(comments, excluded.comments),"
        "   caption = CASE WHEN length(excluded.caption) > length(caption)"
        "                  THEN excluded.caption ELSE caption END",
        (artifact_id, platform, url, author, caption, views, comments, uploaded_at, now, promo),
    )
    return artifact_id


def history(conn: sqlite3.Connection, artifact_id: int) -> dict:
    """When it was first seen and how many sightings it has, for the report's age marker."""
    row = conn.execute("SELECT first_seen, (SELECT COUNT(*) FROM observations o"
                       " WHERE o.artifact_id = artifacts.id) AS n FROM artifacts WHERE id = ?",
                       (artifact_id,)).fetchone()
    return {"first_seen": row[0], "sightings": row[1]}


def display_name(conn: sqlite3.Connection, artifact_id: int) -> str:
    return conn.execute("SELECT name FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()[0]


def gate(conn: sqlite3.Connection, name: str, *, gate: str, value: str, verdict: str,
          cost_micro: int = 0, at: str = "") -> None:
    row = conn.execute("SELECT id FROM artifacts WHERE key = ?", (key(name),)).fetchone()
    if row is None:
        raise KeyError(f"no such artifact: {name}")
    conn.execute(
        "INSERT INTO checks (artifact_id, gate, value, verdict, cost_micro, at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (row[0], gate, value, verdict, cost_micro, at or value),
    )


def record_run(conn, *, day: str, words, discovered: int, posts: int, named: int,
               candidates: int, grown, cost_micro: int, opens: int, at: str = "") -> int:
    """One row per run, so a day can be replayed without reading the report it printed."""
    cur = conn.execute(
        "INSERT INTO runs(day, at, words, discovered, posts, named, candidates, grown, cost_micro, opens)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (day, at or dt.datetime.now().isoformat(timespec="seconds"), ", ".join(words), discovered,
         posts, named, candidates, ", ".join(grown), cost_micro, opens))
    return cur.lastrowid


def verdicts(conn: sqlite3.Connection, name: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT c.gate, c.verdict FROM checks c JOIN artifacts a ON a.id = c.artifact_id"
        " WHERE a.name = ? ORDER BY c.id", (normalize(name),))
    return {r[0]: r[1] for r in rows}


def top(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    rows = conn.execute(
        "SELECT a.name, MAX(o.views) AS views, COUNT(*) AS sightings,"
        " COUNT(DISTINCT o.author) AS creators, MIN(o.uploaded_at) AS oldest"
        " FROM artifacts a JOIN observations o ON o.artifact_id = a.id"
        " GROUP BY a.id ORDER BY views DESC LIMIT ?", (limit,))
    return [dict(r) for r in rows]


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "artifacts": conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
        "observations": conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
        "checks": conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0],
    }


def import_tiktok(conn: sqlite3.Connection, path: Path, names: dict[str, str] | None = None) -> dict[str, int]:
    """Load an Apify tiktok-search dump.

    A post only becomes an observation once the naming step said what it shows: the dump
    knows the query, not the effect. Posts with no name in `names` (keyed by post id) are
    counted and skipped, so nothing enters the store under the wrong name.
    """
    names = names or {}
    seen = skipped = 0
    for post in json.loads(Path(path).read_text()):
        name = names.get(str(post.get("id")))
        if not name:
            skipped += 1
            continue
        observe(
            conn, name, platform="tiktok",
            url=post.get("postPage") or f"tiktok:{post.get('id')}",
            author=(post.get("channel") or {}).get("name", ""),
            caption=post.get("title", ""),
            views=post.get("views") or 0, comments=post.get("comments") or 0,
            uploaded_at=str(post.get("uploadedAtFormatted", "")),
            promo=int(bool(post.get("isSponsored"))),
        )
        seen += 1
    return {"seen": seen, "skipped": skipped}
