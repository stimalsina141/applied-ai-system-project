import pytest

from logic_utils import check_guess, update_score

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    outcome, _ = check_guess(60, 50)
    assert outcome == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    outcome, _ = check_guess(40, 50)
    assert outcome == "Too Low"

def test_hint_direction_matches_outcome():
    # Regression: the hint text used to point the wrong way.
    # A guess that is too high was telling the player to go HIGHER.
    outcome, message = check_guess(60, 50)
    assert outcome == "Too High"
    assert "LOWER" in message
    assert "HIGHER" not in message

    outcome, message = check_guess(40, 50)
    assert outcome == "Too Low"
    assert "HIGHER" in message
    assert "LOWER" not in message

def test_string_secret_compares_numerically():
    # Regression: app.py passes the secret as a str on even attempts.
    # The old fallback compared them as text, so "9" > "50" made a
    # guess of 9 look too high.
    assert check_guess(9, "50")[0] == "Too Low"
    assert check_guess(60, "50")[0] == "Too High"
    assert check_guess(50, "50")[0] == "Win"

@pytest.mark.parametrize("attempt_number", [1, 2, 3, 4, 5, 6])
def test_wrong_guess_always_costs_five(attempt_number):
    # Regression: "Too High" used to ADD 5 points on even-numbered
    # attempts, so guessing wrong could raise your score.
    assert update_score(100, "Too High", attempt_number) == 95
    assert update_score(100, "Too Low", attempt_number) == 95

@pytest.mark.parametrize("attempt_number", [1, 2, 3, 4, 5, 6])
def test_high_and_low_are_penalized_equally(attempt_number):
    # Direction of the miss must not change the penalty.
    assert (
        update_score(100, "Too High", attempt_number)
        == update_score(100, "Too Low", attempt_number)
    )

def test_winning_on_first_try_pays_full():
    # Regression: the formula used to be 100 - 10 * (attempt_number + 1),
    # which charged you for a guess you had not used yet. Winning on
    # attempt 1 paid 80 instead of 90.
    assert update_score(0, "Win", 1) == 90

@pytest.mark.parametrize(
    "attempt_number,expected",
    [(1, 90), (2, 80), (3, 70), (4, 60), (5, 50)],
)
def test_win_payout_drops_ten_per_attempt(attempt_number, expected):
    # Each extra guess should cost exactly 10 points, no more.
    assert update_score(0, "Win", attempt_number) == expected

def test_win_payout_never_drops_below_ten():
    # A very long game should still be worth something.
    assert update_score(0, "Win", 20) == 10
    assert update_score(0, "Win", 100) == 10
