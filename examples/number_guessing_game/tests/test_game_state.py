import random

from game_state import get_range_for_difficulty, init_game, new_game


def test_secret_stays_the_same_across_reruns():
    # Streamlit reruns the whole script after every click, so init_game
    # runs again each time. The secret must only be picked once.
    state = {}
    rng = random.Random(1)
    init_game(state, "Normal", rng)
    first_secret = state["secret"]

    for _ in range(10):
        init_game(state, "Normal", rng)

    assert state["secret"] == first_secret


def test_init_game_keeps_progress_across_reruns():
    state = {}
    init_game(state, "Normal", random.Random(2))
    state["attempts"] = 3
    state["score"] = -15

    init_game(state, "Normal", random.Random(3))

    assert state["attempts"] == 3
    assert state["score"] == -15


def test_new_game_resets_all_state():
    state = {}
    init_game(state, "Normal", random.Random(4))
    state.update(attempts=5, score=40, status="won", history=[10, 50, 63])

    new_game(state, "Normal", random.Random(5))

    assert state["attempts"] == 0
    assert state["score"] == 0
    assert state["status"] == "playing"
    assert state["history"] == []


def test_new_game_respects_difficulty_range():
    for seed in range(50):
        state = {}
        new_game(state, "Easy", random.Random(seed))
        low, high = get_range_for_difficulty("Easy")
        assert low <= state["secret"] <= high
