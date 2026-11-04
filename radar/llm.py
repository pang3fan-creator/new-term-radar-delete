"""One JSON answer per item, with the guarantee that every item got one.

Measured 2026-11-03: on 100 TikTok captions the model dropped 26 rows instead of answering
"none". A short answer therefore means "no answer", never "no" — the missing rows are asked
again, and only rows that come back are read.
"""
from __future__ import annotations

import json

from . import aisa


def ask(model: str, system: str, items: list[dict], field: str, size: int = 50,
        tries: int = 3) -> tuple[dict[int, str], int]:
    """{index: value} for every item the model answered; the number of calls it took."""
    out: dict[int, str] = {}
    todo = list(range(len(items)))
    calls = 0
    for _ in range(tries):
        if not todo:
            break
        missing: list[int] = []
        for start in range(0, len(todo), size):
            batch = todo[start:start + size]
            payload = [dict(items[i], i=k) for k, i in enumerate(batch)]
            calls += 1
            answer = aisa.chat(model, system, json.dumps(payload, ensure_ascii=False), max_tokens=2000)
            left, right = answer.find("["), answer.rfind("]")
            try:
                rows = json.loads(answer[left:right + 1])
            except ValueError:
                missing.extend(batch)
                continue
            seen = set()
            for row in rows if isinstance(rows, list) else []:
                k = row.get("i") if isinstance(row, dict) else None
                if isinstance(k, int) and 0 <= k < len(batch) and k not in seen:
                    seen.add(k)
                    out[batch[k]] = str(row.get(field) or "").strip().lower()
            missing.extend(batch[k] for k in range(len(batch)) if k not in seen)
        todo = missing
    return out, calls
