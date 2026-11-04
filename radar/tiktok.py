"""TikTok as the discovery layer: what is being posted, sorted by date, for a quarter of a cent.

Apify's `tiktok-search-scraper` is pay-per-video ($0.00025) and can sort by upload date, which
is the only ordering that matters here — a trend is old news at 30 days.
"""
from __future__ import annotations

import json
import os
import urllib.request

ACTOR = "xmolodtsov~tiktok-search-scraper"
COST_MICRO = 300  # $0.0003 a video, measured 2026-11-03
COMMENTS_ACTOR = "clockworks~tiktok-comments-scraper"
COMMENT_MICRO = 1250  # $0.00125 a comment


def token() -> str:
    return os.environ.get("APIFY_TOKEN", "")


def search(queries: list[str], per: int = 25, timeout: int = 300) -> tuple[list[dict], int]:
    """Videos for each query, newest first; cost in micro-USD."""
    key = token()
    if not key:
        raise RuntimeError("APIFY_TOKEN is not set")
    body = {"keywords": queries, "maxItemsPerKeyword": per, "sortType": "DATE_POSTED"}
    req = urllib.request.Request(
        f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?timeout={timeout}",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout + 30) as res:
        posts = json.load(res)
    return posts, len(posts) * COST_MICRO


def comments(urls: list[str], per: int = 40, timeout: int = 300) -> tuple[list[str], int]:
    """Text of the first comments under these videos; cost in micro-USD.

    YouTube answers free and is asked first; this is the fallback for an effect that only
    exists on TikTok yet.
    """
    key = token()
    if not key or not urls:
        return [], 0
    body = {"postURLs": urls, "commentsPerPost": per, "maxRepliesPerComment": 0}
    req = urllib.request.Request(
        f"https://api.apify.com/v2/acts/{COMMENTS_ACTOR}/run-sync-get-dataset-items?timeout={timeout}",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout + 30) as res:
        rows = json.load(res)
    texts = [str(r.get("text") or "") for r in rows if r.get("text")]
    return texts, len(texts) * COMMENT_MICRO
