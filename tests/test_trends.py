import datetime as dt

from radar import trends


def _weeks(values, start=dt.date(2025, 11, 2)):
    return [(start + dt.timedelta(weeks=n), v) for n, v in enumerate(values)]


def test_a_phrase_nobody_searches_is_silent():
    assert trends.judge(_weeks([0] * 53))["verdict"] == "silent"
    assert trends.judge([])["verdict"] == "silent"


def test_a_phrase_picking_up_is_rising():
    got = trends.judge(_weeks([10] * 49 + [20, 20, 20, 20]))
    assert got["verdict"] == "rising"
    assert got["ratio"] == 2.0


def test_a_noise_sized_bump_is_not_rising():
    assert trends.judge(_weeks([1] * 49 + [2, 2, 2, 2]))["verdict"] == "flat"


def test_a_year_of_flat_interest_is_flat_not_silent():
    got = trends.judge(_weeks([20] * 53))
    assert got["verdict"] == "flat" and got["now"] == 20.0


def test_a_phrase_that_peaked_months_ago_is_falling():
    values = [5] * 23 + [60, 80, 100, 90, 70, 50, 30] + [3] * 23
    got = trends.judge(_weeks(values))
    assert got["verdict"] == "falling"
    assert got["peak"] == 100
    assert got["peak_day"] == str(dt.date(2025, 11, 2) + dt.timedelta(weeks=25))
