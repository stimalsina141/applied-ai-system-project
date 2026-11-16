"""Game state helpers for the Streamlit guessing game.

`state` is any dict-like object. In the app it is `st.session_state`, which
survives Streamlit reruns; in tests it is a plain dict.
"""
import random

DIFFICULTY_RANGES = {
    "Easy": (1, 20),
    "Normal": (1, 100),
    "Hard": (1, 50),
}


def get_range_for_difficulty(difficulty: str):
    """Return (low, high) inclusive range for a given difficulty."""
    return DIFFICULTY_RANGES.get(difficulty, (1, 100))


def init_game(state, difficulty: str, rng=random):
    """Prepare the game. Streamlit calls this on every rerun of the script."""
    if "secret" not in state:
        low, high = get_range_for_difficulty(difficulty)
        state["secret"] = rng.randint(low, high)
    state.setdefault("attempts", 0)
    state.setdefault("score", 0)
    state.setdefault("status", "playing")
    state.setdefault("history", [])


def new_game(state, difficulty: str, rng=random):
    """Start over when the player clicks "New Game"."""
    low, high = get_range_for_difficulty(difficulty)
    state["secret"] = rng.randint(low, high)
    state["attempts"] = 0
    state["score"] = 0
    state["status"] = "playing"
    state["history"] = []
