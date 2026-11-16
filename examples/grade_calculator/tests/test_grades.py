import pytest

from grades import class_average, letter_grade


@pytest.mark.parametrize(
    "score,expected",
    [(95, "A"), (90, "A"), (89, "B"), (80, "B"), (70, "C"), (60, "D"), (59, "F")],
)
def test_letter_grade_boundaries(score, expected):
    assert letter_grade(score) == expected


def test_class_average_uses_every_score():
    assert class_average([100, 80, 60]) == 80


def test_class_average_single_score():
    assert class_average([72]) == 72
