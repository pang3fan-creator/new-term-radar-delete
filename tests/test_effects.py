"""Offline tests for the fork's chain: naming, want, claim, and the daily that joins them."""
import json

import pytest

from radar import artifacts, claim, effects, llm, naming, want

REAL_DNS = claim.resolves   # the suite stubs DNS globally; these tests want the parser back


def test_ask_asks_again_for_the_rows_the_model_dropped(monkeypatch):
    calls = []

    names = {"a": "toc toc ai dance", "b": "none", "c": "red light filter"}

    def fake_chat(model, system, user, max_tokens=0):
        calls.append(user)
        rows = [{"i": k, "name": names[item["c"]]} for k, item in enumerate(json.loads(user))]
        return json.dumps(rows[:1] if len(calls) == 1 else rows)

    monkeypatch.setattr(llm.aisa, "chat", fake_chat)
    got, calls_made = llm.ask("m", "s", [{"c": "a"}, {"c": "b"}, {"c": "c"}], "name")
    assert got == {0: "toc toc ai dance", 1: "none", 2: "red light filter"}
    assert calls_made == 2


def test_names_keeps_effects_and_drops_none(monkeypatch):
    monkeypatch.setattr(naming.llm, "ask", lambda *a, **k: ({0: "toc toc ai dance", 1: "none"}, 1))
    posts = [{"title": "a", "hashtags": [None, "ai"]}, {"title": "b"}]
    assert naming.names(posts, "m") == ({0: "toc toc ai dance"}, 1)


def test_want_counts_asks_and_ignores_praise(monkeypatch):
    texts = ["how did you do this?", "so funny", "what app is this", "AI is crazy"]
    monkeypatch.setattr(want.llm, "ask",
                        lambda *a, **k: ({0: "want", 1: "react", 2: "want", 3: "react"}, 1))
    got, total, examples, _ = want.share(texts, "m")
    assert (got, total) == (2, 4)
    assert examples[0] == "how did you do this?"


def test_claim_reproduces_the_calibration(monkeypatch):
    pages = {"ai photo shoot": 10, "toc toc ai dance": 68, "thriller ai dance": 76,
             "hotel lobby ai": 1980}
    monkeypatch.setattr(claim.goanyapi, "intitle", lambda term, window="m": (pages[term], 4000))
    monkeypatch.setattr(claim.dotcom, "lookup", lambda d: {"domain": d, "taken": False})
    verdicts = {t: claim.check(t)["verdict"] for t in pages}
    assert verdicts == {"ai photo shoot": "pass", "toc toc ai dance": "busy",
                        "thriller ai dance": "busy", "hotel lobby ai": "busy"}
    assert claim.check("ai photo shoot")["cost_micro"] == 8000   # 10 pages sits on the line: read twice


def test_claim_says_claimed_when_the_com_is_gone(monkeypatch):
    monkeypatch.setattr(claim.goanyapi, "intitle", lambda term, window="m": (5, 4000))
    monkeypatch.setattr(claim.dotcom, "lookup",
                        lambda d: {"domain": d, "taken": True, "registered": "2026-10-18"})
    got = claim.check("toc toc ai dance")
    assert (got["verdict"], got["domain"], got["registered"]) == ("claimed", "taken", "2026-10-18")


def test_daily_keeps_only_what_passes_all_three(tmp_path, monkeypatch):
    posts = [
        {"id": "1", "postPage": "https://t/1", "title": "toc", "views": 900_000,
         "channel": {"name": "a"}, "uploadedAtFormatted": "2026-10-27T00:00:00.000Z"},
        {"id": "2", "postPage": "https://t/2", "title": "toc again", "views": 400_000,
         "channel": {"name": "b"}, "uploadedAtFormatted": "2026-10-29T00:00:00.000Z"},
        {"id": "3", "postPage": "https://t/3", "title": "junk", "views": 800_000,
         "channel": {"name": "c"}, "uploadedAtFormatted": "2026-10-30T00:00:00.000Z"},
    ]
    discover = lambda queries, per: (posts, 900)  # noqa: E731
    name = lambda posts, model: ({0: "toc toc ai dance", 1: "toc toc ai dance", 2: "junk thing"}, 1)  # noqa: E731
    heard = lambda term: (["how do i make this"] * 40, [])  # noqa: E731
    share = lambda texts, model: (12, 40, ["how do i make this"], 1)  # noqa: E731
    checks = {"toc toc ai dance": {"intitle": 12, "domain": "free", "registered": "",
                                   "verdict": "pass", "cost_micro": 4000},
              "junk thing": {"intitle": 400, "domain": "taken", "registered": "2026-01-01",
                             "verdict": "busy", "cost_micro": 4000}}
    check = lambda term: dict(checks[term])  # noqa: E731

    got = effects.run(["q"], {"judge": {"model": "m"}}, tmp_path,
                      discover=discover, name=name, heard=heard, share=share, check=check)
    assert [r["name"] for r in got["rows"]] == ["toc toc ai dance", "junk thing"]
    assert [r["pass"] for r in got["rows"]] == [True, False]
    assert got["rows"][0]["creators"] == {"a", "b"}
    assert got["cost_micro"] == 900 + 4000 + 4000
    text = effects.render(got)
    assert "toc toc ai dance" in text and "junk thing" in text
    assert artifacts.counts(artifacts.connect(tmp_path))["observations"] == 3


def test_views_reads_youtube_display():
    from radar import effects
    assert effects._views("1.2M views") == 1_200_000
    assert effects._views("597,300 views") == 597_300
    assert effects._views("12K views") == 12_000
    assert effects._views("No views") == 0


def _one_row(tmp_path, newest, today):
    posts = [{"id": "1", "postPage": "https://t/1", "title": "x", "views": 900_000,
              "channel": {"name": "a"}, "uploadedAtFormatted": newest + "T00:00:00.000Z"}]
    return effects.run(
        ["q"], {"judge": {"model": "m"}}, tmp_path, today=today,
        discover=lambda queries, per: (posts, 0),
        name=lambda posts, model: ({0: "toc toc ai dance"}, 1),
        heard=lambda term: (["how do i make this"] * 40, []),
        share=lambda texts, model: (12, 40, [], 1),
        check=lambda term: {"intitle": 1, "domain": "free", "registered": "",
                            "verdict": "pass", "cost_micro": 0},
        trend=lambda term: {"verdict": "flat", "now": 40.0, "peak": 100, "peak_day": "",
                            "ratio": 1.0, "value": "40.0/100", "cost_micro": 6_000})


def test_a_week_old_is_cooling_not_open(tmp_path):
    import datetime as dt
    today = dt.date(2026, 11, 10)
    got = _one_row(tmp_path, "2026-10-30", today)  # 11 days: still seen, past its window
    assert got["rows"][0]["reason"] == "cooling"   # the trend came back flat, so the age stands
    assert not got["rows"][0]["pass"]


def test_the_report_says_new_or_since_when(tmp_path):
    import datetime as dt
    got = _one_row(tmp_path, "2026-10-30", dt.date(2026, 10, 31))
    assert got["rows"][0]["is_new"] is True
    assert "new today" in effects.render(got)
    again = _one_row(tmp_path, "2026-10-30", dt.date(2026, 11, 1))
    assert again["rows"][0]["is_new"] is False
    assert "seen since 2026-10-31" in effects.render(again)


def test_a_squatted_ai_ending_counts_as_claimed(monkeypatch):
    monkeypatch.setattr(claim.goanyapi, "intitle", lambda term, window="m": (5, 4000))
    monkeypatch.setattr(claim.dotcom, "lookup", lambda d: {"domain": d, "taken": False})
    monkeypatch.setattr(claim, "resolves",
                        lambda host: host == "celebritysignatureimitation.ai")
    got = claim.check("celebrity signature imitation")
    assert got["verdict"] == "claimed"
    assert got["tld"] == "ai"
    assert got["cost_micro"] == 4000          # DNS costs nothing


def test_the_slug_is_what_gets_registered():
    assert claim.slug("Celebrity Signature Imitation") == "celebritysignatureimitation"
    assert claim.slug("ai dance filter") == "aidancefilter"
    assert claim.slug("") == ""


def test_dns_says_free_when_the_name_does_not_exist(monkeypatch):
    monkeypatch.setattr(claim, "resolves", REAL_DNS)
    monkeypatch.setattr(claim, "_doh", lambda url: {"Status": 3})
    assert claim.resolves("nothinghere.example") is False


def test_dns_says_taken_when_the_name_exists(monkeypatch):
    monkeypatch.setattr(claim, "resolves", REAL_DNS)
    monkeypatch.setattr(claim, "_doh", lambda url: {"Status": 0, "Answer": [{"data": "1.2.3.4"}]})
    assert claim.resolves("something.example") is True


def test_a_broken_lookup_is_not_a_verdict(monkeypatch):
    def boom(url):
        raise OSError("offline")
    monkeypatch.setattr(claim, "resolves", REAL_DNS)
    monkeypatch.setattr(claim, "_doh", boom)
    assert claim.resolves("something.example") is None


def test_youtube_is_asked_first_and_tiktok_only_when_thin(tmp_path):
    import datetime as dt
    seen = {"tiktok": 0}

    def heard(term):
        return ["how do i make this"], []

    def comments(urls, per):
        seen["tiktok"] += 1
        return ["how do i make this"] * 30, 37_500

    posts = [{"id": "1", "postPage": "https://t/1", "title": "x", "views": 900_000,
              "channel": {"name": "a"}, "uploadedAtFormatted": "2026-10-30T00:00:00.000Z"}]
    got = effects.run(
        ["q"], {"judge": {"model": "m"}}, tmp_path, today=dt.date(2026, 10, 31),
        discover=lambda queries, per: (posts, 0),
        name=lambda posts, model: ({0: "toc toc ai dance"}, 1),
        heard=heard, comments=comments,
        share=lambda texts, model: (len(texts), len(texts), [], 0),
        check=lambda term: {"intitle": 1, "domain": "free", "tld": "", "registered": "",
                            "verdict": "pass", "cost_micro": 0})
    assert seen["tiktok"] == 1
    assert got["rows"][0]["total"] == 31
    assert got["cost_micro"] >= 37_500


def test_a_well_covered_effect_pays_tiktok_nothing(tmp_path):
    import datetime as dt

    def comments(urls, per):
        raise AssertionError("must not be paid when YouTube already has enough")

    posts = [{"id": "1", "postPage": "https://t/1", "title": "x", "views": 900_000,
              "channel": {"name": "a"}, "uploadedAtFormatted": "2026-10-30T00:00:00.000Z"}]
    effects.run(
        ["q"], {"judge": {"model": "m"}}, tmp_path, today=dt.date(2026, 10, 31),
        discover=lambda queries, per: (posts, 0),
        name=lambda posts, model: ({0: "toc toc ai dance"}, 1),
        heard=lambda term: (["how do i make this"] * 40, []), comments=comments,
        share=lambda texts, model: (len(texts), len(texts), [], 0),
        check=lambda term: {"intitle": 1, "domain": "free", "tld": "", "registered": "",
                            "verdict": "pass", "cost_micro": 0})


def test_the_day_is_kept_beside_the_latest_report(tmp_path):
    from radar import effects

    one = effects.archive(tmp_path / "report.md", "first", "2026-11-02")
    two = effects.archive(tmp_path / "report.md", "second", "2026-11-03")
    assert one.name == "report-2026-11-02.md" and one.read_text() == "first"
    assert two.read_text() == "second" and one.exists()


def test_a_run_is_written_down_with_what_it_did(tmp_path):
    import datetime as dt

    from radar import artifacts

    posts = [{"id": "1", "postPage": "https://t/1", "title": "x", "views": 900_000,
              "channel": {"name": "a"}, "uploadedAtFormatted": "2026-10-30T00:00:00.000Z"}]
    effects.run(
        ["ai dance filter"], {"judge": {"model": "m"}, "effects": {"grow": 0}}, tmp_path,
        today=dt.date(2026, 10, 31),
        discover=lambda queries, per: (posts, 3_000),
        name=lambda posts, model: ({0: "toc toc ai dance"}, 1),
        heard=lambda term, videos=3: (["how do i make this"] * 25, []),
        comments=lambda urls, per: ([], 0),
        share=lambda texts, model: (25, 25, [], 0),
        check=lambda term: {"intitle": 1, "domain": "free", "tld": "", "registered": "",
                            "verdict": "pass", "cost_micro": 4_000})
    row = artifacts.connect(tmp_path).execute("SELECT * FROM runs").fetchone()
    assert row["day"] == "2026-10-31"
    assert row["words"] == "ai dance filter"
    assert (row["discovered"], row["posts"], row["named"], row["candidates"]) == (1, 1, 1, 1)
    assert row["cost_micro"] == 7_000 and row["opens"] == 1


def test_a_fresh_effect_nobody_searches_is_not_open(tmp_path):
    import datetime as dt

    posts = [{"id": "1", "postPage": "https://t/1", "title": "x", "views": 900_000,
              "channel": {"name": "a"}, "uploadedAtFormatted": "2026-10-30T00:00:00.000Z"}]
    got = effects.run(
        ["q"], {"judge": {"model": "m"}}, tmp_path, today=dt.date(2026, 10, 31),
        discover=lambda queries, per: (posts, 0),
        name=lambda posts, model: ({0: "nostalgia filter"}, 1),
        heard=lambda term, videos=3: (["how do i make this"] * 25, []),
        comments=lambda urls, per: ([], 0),
        share=lambda texts, model: (25, 25, [], 0),
        check=lambda term: {"intitle": 1, "domain": "free", "tld": "", "registered": "",
                            "verdict": "pass", "cost_micro": 0},
        trend=lambda term: {"verdict": "silent", "now": 0.0, "peak": 0, "peak_day": "",
                            "ratio": 0.0, "value": "0.0/0", "cost_micro": 6_000})
    assert got["rows"][0]["reason"] == "demand" and got["rows"][0]["pass"] is False
    assert got["cost_micro"] == 6_000


def test_a_rising_phrase_stays_open_and_costs_one_more_call(tmp_path):
    import datetime as dt

    posts = [{"id": "1", "postPage": "https://t/1", "title": "x", "views": 900_000,
              "channel": {"name": "a"}, "uploadedAtFormatted": "2026-10-30T00:00:00.000Z"}]
    asked = []

    def trend(term):
        asked.append(term)
        return {"verdict": "rising", "now": 40.0, "peak": 60, "peak_day": "2026-10-28",
                "ratio": 4.0, "value": "40.0/60", "cost_micro": 6_000}

    got = effects.run(
        ["q"], {"judge": {"model": "m"}}, tmp_path, today=dt.date(2026, 10, 31),
        discover=lambda queries, per: (posts, 0),
        name=lambda posts, model: ({0: "toc toc ai dance"}, 1),
        heard=lambda term, videos=3: (["how do i make this"] * 25, []),
        comments=lambda urls, per: ([], 0),
        share=lambda texts, model: (25, 25, [], 0),
        check=lambda term: {"intitle": 1, "domain": "free", "tld": "", "registered": "",
                            "verdict": "pass", "cost_micro": 0},
        trend=trend)
    assert asked == ["toc toc ai dance"]
    assert got["rows"][0]["pass"] is True and got["rows"][0]["trend"]["ratio"] == 4.0


def test_a_count_that_disagrees_with_itself_is_not_trusted(monkeypatch):
    from radar import claim

    reads = iter([46, 22500])
    monkeypatch.setattr(claim, "intitle", lambda term: (next(reads), 4_000))
    monkeypatch.setattr(claim, "domain", lambda term: ("free", "", "com", 0))
    got = claim.check("capcut pioneer template")
    assert got["intitle"] is None and got["verdict"] == "unknown"


def test_one_read_is_enough_when_far_from_the_line(monkeypatch):
    from radar import claim

    calls = []
    monkeypatch.setattr(claim, "intitle", lambda term: (calls.append(1) or 900, 4_000))
    monkeypatch.setattr(claim, "domain", lambda term: ("free", "", "com", 0))
    assert claim.check("x filter")["verdict"] == "busy" and len(calls) == 1


def test_a_preset_inside_an_app_is_not_an_effect(monkeypatch):
    from radar import naming

    posts = [{"title": "a"}, {"title": "b"}, {"title": "c"}]
    monkeypatch.setattr(naming.llm, "ask", lambda *a, **k: (
        {0: "capcut pioneer template", 1: "toc toc ai dance", 2: "capcut filter"}, 1))
    got, _ = naming.names(posts, "m")
    assert got == {1: "toc toc ai dance"}


def test_the_category_suffix_is_dropped_from_the_name(monkeypatch):
    from radar import naming

    monkeypatch.setattr(naming.llm, "ask", lambda *a, **k: (
        {0: "im sorry i lied meme", 1: "thriller ai dance", 2: "dance meme"}, 1))
    got, _ = naming.names([{"title": "a"}, {"title": "b"}, {"title": "c"}], "m")
    assert got == {0: "im sorry i lied", 1: "thriller ai dance", 2: "dance meme"}


def test_a_rising_search_is_reported_even_when_the_video_is_not_reproducible(tmp_path):
    import datetime as dt

    from radar import effects

    got = effects.run(
        ["q"], {"judge": {"model": "m"}}, tmp_path, today=dt.date(2026, 11, 3),
        discover=lambda words, per, timeout=0: ([{"title": "im sorry i lied", "views": "900000",
                                                   "comments": 40, "uploadedAtFormatted": "2026-10-21",
                                                   "postPage": "https://tiktok.com/@a/1"}], 1),
        name=lambda posts, model: ({0: "im sorry i lied"}, 0),
        heard=lambda term, videos=3: (["first", "second"], []),
        share=lambda texts, model: (0, 41, [], 0),
        check=lambda term: {"intitle": 6, "domain": "free", "tld": "com", "registered": "",
                            "verdict": "pass", "cost_micro": 0},
        comments=lambda urls, per: ([], 0),
        trend=lambda term: {"verdict": "rising", "now": 50.0, "peak": 100, "peak_day": "2026-10-28",
                            "value": "50/100", "cost_micro": 6000},
    )
    row = got["rows"][0]
    assert row["reason"] == "rising" and row["pass"] is False and got["cost_micro"] == 6_001
