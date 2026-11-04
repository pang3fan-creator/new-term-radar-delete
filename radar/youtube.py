"""YouTube, used for the one thing it is free at: reading what people say under a video.

Search is a single page request (`ytInitialData`); comments come from yt-dlp. No API key, no
quota, no per-comment price — which is why the judgment layer lives here and not on TikTok,
where a comment costs $0.00125.

yt-dlp needs a JavaScript runtime for YouTube's player data. Without one it still runs, but
view counts come back wrong and comments empty, so `available()` says whether to trust it.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+1",
}
PER_VIDEO = 40


def binary() -> str:
    """A yt-dlp we keep, because `uv run --with yt-dlp` costs 15 s of resolving per call."""
    found = shutil.which("yt-dlp")
    if found:
        return found
    venv = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "new-term-radar" / "yt"
    exe = venv / "bin" / "yt-dlp"
    if not exe.exists():
        subprocess.run(["uv", "venv", "--quiet", str(venv)], check=True, timeout=300)
        subprocess.run(["uv", "pip", "install", "--quiet", "--python", str(venv / "bin" / "python"),
                        "yt-dlp"], check=True, timeout=300)
    return str(exe)


def available() -> bool:
    return shutil.which("uv") is not None or shutil.which("yt-dlp") is not None


def search(query: str, n: int = 3) -> list[dict]:
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as res:
        page = res.read().decode("utf-8", "replace")
    found = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S)
    if not found:
        return []
    rows: list[dict] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, shape in (("videoRenderer", "title"), ("reelItemRenderer", "headline")):
                item = node.get(key)
                if isinstance(item, dict):
                    head = item.get(shape) or {}
                    rows.append({
                        "id": item.get("videoId"),
                        "title": (head.get("runs") or [head]).pop().get("text", "")[:200]
                        if isinstance(head, dict) else "",
                        "age": (item.get("publishedTimeText") or {}).get("simpleText", ""),
                        "views": (item.get("viewCountText") or {}).get("simpleText", ""),
                        "channel": (((item.get("ownerText") or {}).get("runs") or [{}])[0]
                                    .get("text") or ""),
                    })
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(found.group(1)))
    return rows[:n]


def comments(video_id: str, n: int = PER_VIDEO) -> list[str]:
    """The top comments under one video, best first. Empty when the video has none."""
    cmd = [binary(), f"https://www.youtube.com/watch?v={video_id}", "--skip-download", "--write-comments",
           "-J", "--extractor-args", f"youtube:comment_sort=top;max_comments={n},all,0"]
    if shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        data = json.loads(proc.stdout) or {}
    except (subprocess.SubprocessError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    return [(c.get("text") or "").strip() for c in (data.get("comments") or [])
            if isinstance(c, dict) and (c.get("text") or "").strip()]


def url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def heard(term: str, videos: int = 3) -> tuple[list[str], list[dict]]:
    """(comments, the videos they came from). The videos are evidence: a verdict that cannot be
    traced to a URL is a rumour."""
    texts: list[str] = []
    used: list[dict] = []
    for hit in search(term, videos):
        if not hit.get("id"):
            continue
        used.append(hit)
        texts.extend(comments(hit["id"]))
    return texts, used
