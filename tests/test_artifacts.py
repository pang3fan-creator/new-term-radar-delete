"""Offline tests for radar/artifacts.py — the fork's memory. No network."""
import json

from radar import artifacts

FIXTURE = "tests/fixtures/tiktok-search-100.json"


def test_one_artifact_per_effect_whatever_the_spacing():
    conn = artifacts.connect(":memory:" if False else _tmp())
    artifacts.observe(conn, "Toc Toc  AI Dance", platform="tiktok", url="u1")
    artifacts.observe(conn, "toc toc ai dance", platform="youtube", url="u2")
    assert artifacts.counts(conn)["artifacts"] == 1
    assert artifacts.counts(conn)["observations"] == 2


def test_same_url_is_one_sighting_and_views_only_grow():
    conn = artifacts.connect(_tmp())
    artifacts.observe(conn, "red light filter", platform="tiktok", url="u1", views=10)
    artifacts.observe(conn, "red light filter", platform="tiktok", url="u1", views=3)
    row = conn.execute("SELECT views FROM observations").fetchone()
    assert row[0] == 10
    assert artifacts.counts(conn)["observations"] == 1


def test_checks_attach_to_the_effect():
    conn = artifacts.connect(_tmp())
    artifacts.observe(conn, "nostalgia capcut filter", platform="tiktok", url="u1")
    artifacts.gate(conn, "nostalgia capcut filter", gate="want", value="0.26",
                    verdict="pass", cost_micro=50_000)
    artifacts.gate(conn, "nostalgia capcut filter", gate="intitle", value="9", verdict="pass")
    assert artifacts.verdicts(conn, "Nostalgia CapCut Filter") == {
        "want": "pass", "intitle": "pass"}
    assert artifacts.counts(conn)["checks"] == 2


def test_top_counts_creators_and_orders_by_peak_views():
    conn = artifacts.connect(_tmp())
    for i, (name, author, views) in enumerate([
        ("small thing", "a", 100),
        ("big thing", "a", 900_000),
        ("big thing", "b", 500),
        ("big thing", "b", 250_000),
    ]):
        artifacts.observe(conn, name, platform="tiktok", url=f"u{i}", author=author, views=views)
    top = artifacts.top(conn)
    assert [r["name"] for r in top] == ["big thing", "small thing"]
    assert top[0] == {"name": "big thing", "views": 900_000, "sightings": 3,
                      "creators": 2, "oldest": ""}


def test_import_skips_posts_the_naming_step_did_not_name(tmp_path):
    dump = [{"id": "1", "keyword": "q", "postPage": "p1", "views": 5},
            {"id": "2", "keyword": "q", "postPage": "p2", "views": 7}]
    path = tmp_path / "dump.json"
    path.write_text(json.dumps(dump))
    conn = artifacts.connect(tmp_path / "state")
    got = artifacts.import_tiktok(conn, path, {"1": "toc toc ai dance"})
    assert got == {"seen": 1, "skipped": 1}
    assert artifacts.counts(conn) == {"artifacts": 1, "observations": 1, "checks": 0}


def test_import_of_the_real_dump_reads_every_post(tmp_path):
    posts = json.loads(open(FIXTURE).read())
    names = {str(p["id"]): "effect one" for p in posts[:3]}
    conn = artifacts.connect(tmp_path / "state")
    got = artifacts.import_tiktok(conn, FIXTURE, names)
    assert got == {"seen": 3, "skipped": len(posts) - 3}
    row = conn.execute("SELECT views, comments, author, url FROM observations"
                       " ORDER BY views DESC LIMIT 1").fetchone()
    assert row[0] > 0 and row[1] >= 0 and row[2] and row[3].startswith("https://www.tiktok.com/")


def _tmp():
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp())


def test_drifted_names_are_one_artifact(tmp_path):
    conn = artifacts.connect(tmp_path)
    first = artifacts.observe(conn, "jeremy clarkson ai filter", platform="tiktok",
                              url="https://t/1", seen_at="2026-11-01")
    again = artifacts.observe(conn, "jeremy clarkson capcut filter", platform="tiktok",
                              url="https://t/2", seen_at="2026-11-02")
    assert first == again
    assert artifacts.counts(conn)["artifacts"] == 1
    assert artifacts.counts(conn)["observations"] == 2
    assert artifacts.display_name(conn, first) == "jeremy clarkson ai filter"


def test_key_drops_modifiers_but_keeps_content():
    assert artifacts.key("Capcut Filter Jeremy Clarkson") == artifacts.key("jeremy clarkson")
    assert artifacts.key("ai dance filter") != artifacts.key("angry dance filter")
    assert artifacts.key("nostalgia ai filter") == artifacts.key("nostalgia filter")


def test_connecting_twice_does_not_split_again(tmp_path):
    artifacts.observe(artifacts.connect(tmp_path), "nostalgia ai filter", platform="tiktok", url="u")
    conn = artifacts.connect(tmp_path)
    assert artifacts.counts(conn)["artifacts"] == 1
