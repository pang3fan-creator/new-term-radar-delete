import datetime as dt
import json

from radar import artifacts, queries


def _db(tmp_path):
    return artifacts.connect(tmp_path)


def test_a_word_is_kept_once_and_reads_back(tmp_path):
    conn = _db(tmp_path)
    assert queries.add(conn, ["ai pet filter", "AI Pet Filter", " ai pet  filter "], queries.GROWN,
                       "2026-11-03") == ["ai pet filter"]
    assert queries.tried(conn) == {"ai pet filter"}


def test_seeds_run_first_and_grown_words_rotate(tmp_path):
    conn = _db(tmp_path)
    queries.add(conn, ["z pet filter", "a pet filter", "b dog filter"], queries.GROWN, "2026-11-01")
    queries.done(conn, ["a pet filter"], "2026-11-02")
    got = queries.due(conn, ["ai dance filter", "capcut filter"], limit=4)
    assert got[:2] == ["ai dance filter", "capcut filter"]
    assert got[2:] == ["z pet filter", "b dog filter"]   # first in first out, not alphabetical
    assert queries.due(conn, ["ai dance filter"], limit=1) == ["ai dance filter"]


def test_plan_keeps_only_phrases_a_person_would_type(monkeypatch):
    answer = json.dumps([
        "ai pet filter",                 # keep
        "jeremy clarkson filter",        # a name it already found
        "how to make a filter",          # a tutorial
        "AI Dog Dance Trend",            # keep, lowercased
        "too many words in one query here",
        "ai dance filter",               # already tried
        "ai baby podcast",               # keep
        "capcut tutorial",               # brand + tutorial
    ])
    monkeypatch.setattr(queries.aisa, "chat", lambda *a, **k: answer)
    got, calls = queries.plan(["jeremy clarkson filter"], {"ai dance filter"}, "m", want=5)
    assert calls == 1
    assert got == ["ai pet filter", "ai dog dance trend", "ai baby podcast"]


def test_plan_gives_up_instead_of_guessing(monkeypatch):
    monkeypatch.setattr(queries.aisa, "chat", lambda *a, **k: "I could not think of any.")
    got, calls = queries.plan(["x filter"], set(), "m")
    assert got == [] and calls == 1


def test_plan_stops_at_want(monkeypatch):
    monkeypatch.setattr(queries.aisa, "chat", lambda *a, **k: json.dumps(
        [f"ai thing {n} filter" for n in range(20)]))
    got, _ = queries.plan([], set(), "m", want=3)
    assert len(got) == 3


def test_a_run_grows_tomorrows_words(tmp_path, monkeypatch):
    from radar import effects

    post = {"id": "1", "postPage": "https://tiktok.com/@a/1", "title": "capcut filter",
            "views": 100_000, "comments": 40, "uploadedAtFormatted": "2026-11-02 10:00:00",
            "channel": {"name": "a"}, "isSponsored": False, "keyword": "ai dance filter"}
    monkeypatch.setattr(queries.aisa, "chat", lambda *a, **k: json.dumps(["ai dog filter"]))
    result = effects.run(["ai dance filter"], {"judge": {"model": "m"}, "effects": {"grow": 2}},
                         tmp_path, per=5, today=dt.date(2026, 11, 3),
                         discover=lambda q, per: ([post], 0),
                         name=lambda posts, model: ({0: "ai pet filter"}, 1),
                         heard=lambda term, videos=3: ([], []),
                         comments=lambda urls, per=40: ([], 0),
                         share=lambda texts, model: (0, 0, [], 0),
                         check=lambda term: {"intitle": 0, "domain": "free", "registered": "",
                                              "verdict": "pass", "cost_micro": 0, "tld": "com"},
                         grow_plan=queries.plan)
    assert result["grown"] == ["ai dog filter"]        # never the name it just found
    assert queries.tried(artifacts.connect(tmp_path)) >= {"ai dog filter", "ai dance filter"}
