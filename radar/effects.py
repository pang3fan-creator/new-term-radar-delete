"""The fork's daily: find effects on TikTok, judge them for free, keep the ones still open.

discover  TikTok search, newest first, $0.0003 a video
name      gate 1 — what is this thing, in words a stranger would type
want      gate 2 — do the comments under it ask how to make it (YouTube, free)
claim     gate 3 — how many pages already target it, does the .com still exist

Everything that passes is stored in radar/artifacts.py so tomorrow's run knows it was seen.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

from . import artifacts, claim, i18n, naming, queries as vocab, tiktok, trends, want, youtube

TOP = 4
MIN_VIEWS = 5_000
FRESH_DAYS = 14
COOL_DAYS = 7
MIN_COMMENTS = 20
PER_RUN = 8


def _day(post: dict) -> str:
    return str(post.get("uploadedAtFormatted") or "")[:10]


def fresh(posts: list[dict], today: dt.date | None = None) -> list[dict]:
    """A trend is old news at two weeks: an August video with 9M views is not a window."""
    cutoff = ((today or dt.date.today()) - dt.timedelta(days=FRESH_DAYS)).isoformat()
    return [p for p in posts if _day(p) >= cutoff]


def _views(text: str) -> int:
    """'1.2M views' -> 1200000. YouTube prints a display string, not a number."""
    found = re.match(r"([\d.]+)\s*([KMB]?)", str(text).replace(",", ""))
    if not found:
        return 0
    scale = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[found.group(2)]
    return int(float(found.group(1)) * scale)


def group(posts: list[dict], named: dict[int, str]) -> list[dict]:
    """One row per effect name, carrying every video that shows it."""
    rows: dict[str, dict] = {}
    for i, post in enumerate(posts):
        name = named.get(i)
        if not name:
            continue
        row = rows.setdefault(name, {"name": name, "posts": [], "views": 0, "creators": set(),
                                     "oldest": ""})
        row["posts"].append(post)
        row["views"] = max(row["views"], int(post.get("views") or 0))
        row.setdefault("newest", "")
        row["creators"].add((post.get("channel") or {}).get("name") or "")
        day = _day(post)
        if day and (not row["oldest"] or day < row["oldest"]):
            row["oldest"] = day
        if day > row["newest"]:
            row["newest"] = day
    return sorted(rows.values(), key=lambda r: r["views"], reverse=True)


def run(queries: list[str], cfg: dict, state: Path, *, per: int = 25,
        today: dt.date | None = None, top: int | None = None,
        discover=tiktok.search, name=naming.names, heard=youtube.heard,
        comments=tiktok.comments, grow_plan=vocab.plan, trend=trends.check,
        share=want.share, check=claim.check) -> dict:
    day = today or dt.date.today()
    settings = cfg.get("effects") or {}
    cool_days = int(settings.get("cool_days", COOL_DAYS))
    grow = int(settings.get("grow", 0))
    model = cfg["judge"]["model"]
    conn = artifacts.connect(state)
    for seed in queries:   # the seeds live in the config; the table only adds to them
        vocab.add(conn, [seed], vocab.SEED, day.isoformat())
    words = vocab.due(conn, queries, limit=int(settings.get("per_run", PER_RUN)))
    found, spent = discover(words, per)
    vocab.done(conn, words, day.isoformat())
    posts = fresh(found, day)
    named, calls = name(posts, model)
    rows = [r for r in group(posts, named) if r["views"] >= MIN_VIEWS][:top or TOP]
    seen_ids: set[int] = set()
    kept: list[dict] = []
    for row in rows:
        artifact_id = 0
        for post in row["posts"]:
            seen_id = artifacts.observe(
                conn, row["name"], platform="tiktok",
                url=post.get("postPage") or f"tiktok:{post.get('id')}",
                author=(post.get("channel") or {}).get("name", ""),
                caption=post.get("title", ""), views=int(post.get("views") or 0),
                comments=int(post.get("comments") or 0),
                uploaded_at=_day(post), seen_at=day.isoformat(),
                promo=int(bool(post.get("isSponsored"))))
            artifact_id = artifact_id or seen_id
        if artifact_id in seen_ids:
            continue
        seen_ids.add(artifact_id)
        row["name"] = artifacts.display_name(conn, artifact_id)
        row.update(artifacts.history(conn, artifact_id))
        row["is_new"] = str(row["first_seen"])[:10] >= day.isoformat()
        kept.append(row)
        texts, seen = heard(row["name"])
        for hit in seen:
            artifacts.observe(conn, row["name"], platform="youtube", url=youtube.url(hit["id"]),
                              seen_at=day.isoformat(),
                              author=hit.get("channel", ""), caption=hit.get("title", ""),
                              views=_views(hit.get("views", "")))
        if len(texts) < MIN_COMMENTS:   # YouTube does not know this effect yet: pay TikTok for its comments
            more, paid = comments([p.get("postPage") or "" for p in row["posts"][:2]], 40)
            texts += more
            spent += paid
        got, total, examples, calls_want = share(texts, model)
        calls += calls_want
        verdict = check(row["name"])
        paid = verdict.pop("cost_micro")
        spent += paid
        row.update({"want": got, "total": total, "examples": examples, **verdict})
        want_ok = total >= MIN_COMMENTS and got / total >= want.WANT
        if verdict["verdict"] != "pass":
            row["reason"] = verdict["verdict"]
        elif total == 0:
            row["reason"] = "silent"
        elif total < MIN_COMMENTS:
            row["reason"] = "thin"
        elif row["newest"] and dt.date.fromisoformat(row["newest"]) < day - dt.timedelta(days=cool_days):
            row["reason"] = "cooling"  # the posts are old news; a window closes in days
        else:
            row["reason"] = "open" if want_ok else "cold"
        row["pass"] = row["reason"] == "open"
        # Closed on the video alone (nobody asks how, or the clips are old) still deserves the
        # priced question: a meme can peak a week after the clip, and a page can ride that.
        if verdict["verdict"] == "pass" and row["reason"] in ("open", "cold", "cooling"):
            demand = trend(row["name"])
            paid_trend = demand.pop("cost_micro", 0)
            spent += paid_trend
            row["trend"] = demand
            if row["pass"] and demand["verdict"] != "rising":
                row["pass"] = False
                row["reason"] = "demand" if demand["verdict"] == "silent" else "fading"
            elif not row["pass"] and demand["verdict"] == "rising":
                row["reason"] = "rising"   # demand is there, but it is watched, not re-made
            artifacts.gate(conn, row["name"], gate="trend", value=demand["value"],
                           verdict=demand["verdict"], cost_micro=paid_trend, at=day.isoformat())
        artifacts.gate(conn, row["name"], gate="want", value=f"{got}/{total}",
                       verdict="pass" if want_ok else ("thin" if total < MIN_COMMENTS else "fail"),
                       cost_micro=0, at=day.isoformat())
        artifacts.gate(conn, row["name"], gate="claim", value=f"{verdict['intitle']}/{verdict['domain']}",
                       verdict=verdict["verdict"], cost_micro=paid, at=day.isoformat())
    grown: list[str] = []
    if grow and named:
        grown, extra = grow_plan(sorted(set(named.values())), vocab.tried(conn), model, want=grow)
        vocab.add(conn, grown, vocab.GROWN, day.isoformat())
        calls += extra
    artifacts.record_run(conn, day=day.isoformat(), words=words, discovered=len(found),
                         posts=len(posts), named=len(named), candidates=len(rows), grown=grown,
                         cost_micro=spent, opens=sum(1 for row in kept if row["pass"]))
    return {"rows": kept, "cost_micro": spent, "calls": calls, "posts": len(posts),
            "named": len(named), "grown": grown, "words": words, "day": day.isoformat()}


def _grown(result: dict) -> str:
    words = result.get("grown") or []
    return i18n.t("fx_grown", words=", ".join(words)) + "\n" if words else ""


def render(result: dict) -> str:
    rows = result["rows"]
    cost = i18n.t("fx_cost", usd=f"${result['cost_micro'] / 1e6:.3f}",
                  posts=result["posts"], named=result["named"])
    if not rows:
        return i18n.t("fx_none") + "\n" + cost + "\n" + _grown(result)
    out = [i18n.t("fx_h"), ""]
    for row in rows:
        mark = i18n.t("fx_open") if row["pass"] else i18n.t(f"fx_verdict_{row['reason']}")
        age = i18n.t("fx_new") if row.get("is_new") else \
            i18n.t("fx_seen", day=str(row.get("first_seen", "?"))[:10])
        out.append(f"**{row['name']}** — {mark} · {age}")
        key = "fx_evidence_one" if len(row["creators"]) == 1 else "fx_evidence"
        out.append("  " + i18n.t(key, views=f"{row['views']:,}",
                                 creators=len(row["creators"]), newest=row["newest"] or "?"))
        pct = round(row["want"] / row["total"] * 100) if row["total"] else 0
        out.append("  " + i18n.t("fx_want", pct=pct, got=row["want"], total=row["total"]))
        pages = row["intitle"] if row["intitle"] is not None else "?"
        domain = i18n.t(f"fx_domain_{row['domain']}", day=row["registered"] or "?",
                        tld=row.get("tld") or "?")
        out.append("  " + i18n.t("fx_claim", pages=pages, domain=domain))
        if row.get("trend"):
            out.append("  " + i18n.t("fx_trend", now=row["trend"]["now"], peak=row["trend"]["peak"],
                                     day=row["trend"]["peak_day"] or "?"))
        for text in row["examples"][:2]:
            out.append(f"  > {text}")
        out.append("")
    out.append(cost)
    return "\n".join(out) + "\n" + _grown(result)


def archive(path, text: str, day: str) -> Path:
    """Keep the day's report beside the latest one: the latest is overwritten, the day's is not."""
    out = Path(path)
    copy = out.with_name(f"{out.stem}-{day}{out.suffix or '.md'}")
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_text(text)
    return copy


def cmd(args, cfg: dict, state: Path) -> int:
    i18n.set_lang(cfg.get("lang", "en"))
    settings = cfg.get("effects") or {}
    queries = args.names or settings.get("queries") or []
    if not queries:
        print(i18n.t("fx_no_queries"), file=sys.stderr)
        return 2
    result = run(queries, cfg, state, per=getattr(args, "per", None) or settings.get("per", 25),
                 top=settings.get("top", TOP))
    text = render(result)
    if args.out:
        Path(args.out).write_text(text)
        archive(args.out, text, result["day"])
        print(text)
    else:
        print(text)
    return 0 if result["rows"] else 1
