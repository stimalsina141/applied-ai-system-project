# Transcript: Number guessing game (Project 1) (session 6cf693a5)

## Explanation shown to the learner

The secret number is supposed to be initialized once when the game starts, but it is being re-initialized every time the game is played. This is causing the secret number to change every time the user clicks Submit. Additionally, the hints are not being calculated correctly because the secret number is not being updated properly. The score calculation is also incorrect because it is not taking into account the number of attempts or the difficulty level.

## Attempt 1: Initialize the secret number once and reuse it across game runs.

Blocked by guardrail: Edit 1 (game_state.py, init_game): `new_code` must be the complete function, starting with `def init_game(`, and nothing else.

## Attempt 2: Initialize the secret number once and reuse it across game runs.

Blocked by guardrail: Edit 1 (game_state.py, init_game): `new_code` must be the complete function, starting with `def init_game(`, and nothing else.

## Attempt 3: Initialize the secret number once and reuse it across game runs.

```diff
--- a/game_state.py
+++ b/game_state.py
@@ -18,13 +18,13 @@
 
 
 def init_game(state, difficulty: str, rng=random):
-    """Prepare the game. Streamlit calls this on every rerun of the script."""
     low, high = get_range_for_difficulty(difficulty)
-    state["secret"] = rng.randint(low, high)
-    state.setdefault("attempts", 0)
-    state.setdefault("score", 0)
-    state.setdefault("status", "playing")
-    state.setdefault("history", [])
+    if 'secret' not in state:
+        state['secret'] = rng.randint(low, high)
+    state.setdefault('attempts', 0)
+    state.setdefault('score', 0)
+    state.setdefault('status', 'playing')
+    state.setdefault('history', [])
 
 
 def new_game(state, difficulty: str, rng=random):
```

Tests: 12 passed, 16 failed in 0.53s (kept: failures went from 17 to 16)

Analysis: Retry the tests to see if the issues are resolved.

# Debugging Report

**Status:** Partially fixed
**Why it stopped:** Stopped after 3 attempts.
**Attempts used:** 3 of 3

## Problem

The secret number changes every time I click Submit. The hints also seem to point the wrong way, my score sometimes goes up after a wrong guess, and New Game doesn't fully restart.

## Root cause

The secret number is not being initialized correctly, and the hints and score calculation are not handling the game state properly.

Confidence: high

- **Confirmed** `game_state.py` `init_game` (lines 24): Secret number is not initialized correctly.
- **Confirmed** `logic_utils.py` `check_guess` (lines 34): Hints are incorrect.
- **Confirmed** `logic_utils.py` `update_score` (lines 45): Score calculation is incorrect.

## Changes made

- **Attempt 3** (`game_state.py` `init_game`): The secret number is now initialized once and reused across game runs.
  - Assumption: The `rng` parameter is a random number generator.

Attempts that were not kept:
- Attempt 1: blocked by a guardrail (Edit 1 (game_state.py, init_game): `new_code` must be the complete function, starting with `def init_game(`, and nothing else.)
- Attempt 2: blocked by a guardrail (Edit 1 (game_state.py, init_game): `new_code` must be the complete function, starting with `def init_game(`, and nothing else.)

## Validation

- Before: 11 passed, 17 failed in 0.39s
- After: 12 passed, 16 failed in 0.53s

| Check | Result |
|---|---|
| Original bug addressed | 1 of 17 failing tests now pass |
| Existing tests preserved | 11 of 11 still pass |
| Full test suite | 12 passed, 16 failed in 0.53s |
| Unrelated behavior changed | Not detected |

## Concept learned

Understood the importance of checking if a key exists in a dictionary before attempting to access it, to prevent errors.

## Code quality

No issues found.

Suggested tests:
- Test the behavior of `init_game` when the `secret` is already set in the state.
- Test the behavior of `new_game` when the `secret` is already set in the state.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 0.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 1.
- Test the behavior of `update_score` when the `outcome` is 'Too High' and the `attempt_number` is 1.
- Test the behavior of `update_score` when the `outcome` is 'Too Low' and the `attempt_number` is 1.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 2.
- Test the behavior of `update_score` when the `outcome` is 'Too High' and the `attempt_number` is 2.
- Test the behavior of `update_score` when the `outcome` is 'Too Low' and the `attempt_number` is 2.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 3.
- Test the behavior of `update_score` when the `outcome` is 'Too High' and the `attempt_number` is 3.
- Test the behavior of `update_score` when the `outcome` is 'Too Low' and the `attempt_number` is 3.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 4.
- Test the behavior of `update_score` when the `outcome` is 'Too High' and the `attempt_number` is 4.
- Test the behavior of `update_score` when the `outcome` is 'Too Low' and the `attempt_number` is 4.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 5.
- Test the behavior of `update_score` when the `outcome` is 'Too High' and the `attempt_number` is 5.
- Test the behavior of `update_score` when the `outcome` is 'Too Low' and the `attempt_number` is 5.
- Test the behavior of `update_score` when the `outcome` is 'Win' and the `attempt_number` is 6.
- Test the behavior of `update_score` when the `outcome` is 'Too High' and the `attempt_number` is 6.
- Test the behavior of `update_score` when the `outcome` is 'Too Low' and the `attempt_number` is 6.

## Remaining concerns

- `test_game_logic::test_hint_direction_matches_outcome` still fails: AssertionError: assert 'LOWER' in '📈 Go HIGHER!'
- `test_game_logic::test_string_secret_compares_numerically` still fails: AssertionError: assert 'Too High' == 'Too Low'
  
  - Too Low
  + Too High
- `test_game_logic::test_wrong_guess_always_costs_five[2]` still fails: AssertionError: assert 105 == 95
 +  where 105 = update_score(100, 'Too High', 2)
- `test_game_logic::test_wrong_guess_always_costs_five[4]` still fails: AssertionError: assert 105 == 95
 +  where 105 = update_score(100, 'Too High', 4)
- `test_game_logic::test_wrong_guess_always_costs_five[6]` still fails: AssertionError: assert 105 == 95
 +  where 105 = update_score(100, 'Too High', 6)
- `test_game_logic::test_high_and_low_are_penalized_equally[2]` still fails: AssertionError: assert 105 == 95
 +  where 105 = update_score(100, 'Too High', 2)
 +  and   95 = update_score(100, 'Too Low', 2)
- `test_game_logic::test_high_and_low_are_penalized_equally[4]` still fails: AssertionError: assert 105 == 95
 +  where 105 = update_score(100, 'Too High', 4)
 +  and   95 = update_score(100, 'Too Low', 4)
- `test_game_logic::test_high_and_low_are_penalized_equally[6]` still fails: AssertionError: assert 105 == 95
 +  where 105 = update_score(100, 'Too High', 6)
 +  and   95 = update_score(100, 'Too Low', 6)
- `test_game_logic::test_winning_on_first_try_pays_full` still fails: AssertionError: assert 80 == 90
 +  where 80 = update_score(0, 'Win', 1)
- `test_game_logic::test_win_payout_drops_ten_per_attempt[1-90]` still fails: AssertionError: assert 80 == 90
 +  where 80 = update_score(0, 'Win', 1)
- `test_game_logic::test_win_payout_drops_ten_per_attempt[2-80]` still fails: AssertionError: assert 70 == 80
 +  where 70 = update_score(0, 'Win', 2)
- `test_game_logic::test_win_payout_drops_ten_per_attempt[3-70]` still fails: AssertionError: assert 60 == 70
 +  where 60 = update_score(0, 'Win', 3)
- `test_game_logic::test_win_payout_drops_ten_per_attempt[4-60]` still fails: AssertionError: assert 50 == 60
 +  where 50 = update_score(0, 'Win', 4)
- `test_game_logic::test_win_payout_drops_ten_per_attempt[5-50]` still fails: AssertionError: assert 40 == 50
 +  where 40 = update_score(0, 'Win', 5)
- `test_game_state::test_new_game_resets_all_state` still fails: assert 40 == 0
- `test_game_state::test_new_game_respects_difficulty_range` still fails: assert 50 <= 20
- Suggested next step: Retry the tests to see if the issues are resolved.
