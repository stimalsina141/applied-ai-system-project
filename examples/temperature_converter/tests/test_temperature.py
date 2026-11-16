import pytest

from temperature import celsius_to_fahrenheit, fahrenheit_to_celsius, is_freezing


def test_boiling_point_to_fahrenheit():
    assert celsius_to_fahrenheit(100) == pytest.approx(212)


def test_boiling_point_to_celsius():
    assert fahrenheit_to_celsius(212) == pytest.approx(100)


def test_round_trip():
    assert fahrenheit_to_celsius(celsius_to_fahrenheit(37)) == pytest.approx(37)


def test_zero_is_freezing():
    assert is_freezing(0)
    assert is_freezing(-5)
    assert not is_freezing(3)
