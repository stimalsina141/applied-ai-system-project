# 🎮 Game Glitch Investigator: The Impossible Guesser

## 🚨 The Situation

You asked an AI to build a simple "Number Guessing Game" using Streamlit.
It wrote the code, ran away, and now the game is unplayable. 

- You can't win.
- The hints lie to you.
- The secret number seems to have commitment issues.

## 🛠️ Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the broken app: `python -m streamlit run app.py`

## 🕵️‍♂️ Your Mission

1. **Play the game.** Open the "Developer Debug Info" tab in the app to see the secret number. Try to win.
2. **Find the State Bug.** Why does the secret number change every time you click "Submit"? Ask ChatGPT: *"How do I keep a variable from resetting in Streamlit when I click a button?"*
3. **Fix the Logic.** The hints ("Higher/Lower") are wrong. Fix them.
4. **Refactor & Test.** - Move the logic into `logic_utils.py`.
   - Run `pytest` in your terminal.
   - Keep fixing until all tests pass!

## 📝 Document Your Experience

### The game's purpose

This is a number guessing game built with Streamlit. The app picks a secret
number in a range that depends on the difficulty you choose, and you try to
guess it before you run out of attempts. After each guess the game tells you
whether you were too high or too low, and your score goes up or down based on
how you did. The point of the project is not really the game itself, it is
that the starter version was full of bugs on purpose, so the job was to play
it, find what was wrong, fix it, and then move the logic into its own file
with tests around it.

### Bugs I found

| # | Bug | What happened |
| - | --- | ------------- |
| 1 | Hints were backwards | A guess above the secret was correctly labelled "Too High" but the message said *"Go HIGHER!"*. Every hint pointed away from the answer, so following them made things worse. |
| 2 | Secret compared as text | `check_guess` had a `try / except` that compared the guess and secret as text if the normal comparison failed. `app.py` was passing the secret as a string every other turn, and because `"9" > "50"` is `True` in Python, small guesses were reported as too high. |
| 3 | Wrong guesses could raise your score | In `update_score`, a "Too High" guess *added* 5 points on even numbered attempts instead of subtracting 5, while "Too Low" always subtracted 5. |
| 4 | Win score was off by one | The payout used `100 - 10 * (attempt_number + 1)`, and `app.py` also incremented the attempt counter before scoring, so you got charged twice for the same guess. Winning on the first try paid 70 instead of 90. |
| 5 | First attempt was not counted | The attempt counter started at 1 on a fresh page but at 0 after clicking "New Game", so the same first-try win paid a different amount depending on how you got there. |
| 6 | Starter tests were broken | Three tests compared the whole result to a single string, but `check_guess` returns two values, the outcome and the hint message. |

Two more bugs that I found but chose not to fix, since they were outside what
I was working on:

- **"New Game" does not fully restart.** It resets the attempts and the secret
  number but not the score, status or history, so after you win you keep
  getting *"You already won"* until you refresh the page.
- **"New Game" ignores the difficulty.** It always picks a number between 1
  and 100, so on Easy you can end up with a secret of 98 even though the
  range says 1 to 20.

### Fixes I applied

1. **Fixed the hint direction** in `check_guess` so "Too High" shows
   *"Go LOWER!"* and "Too Low" shows *"Go HIGHER!"*.
2. **Removed the text comparison fallback** and cast both the guess and the
   secret with `int()` at the top of `check_guess`, so the comparison is
   always numeric no matter what type the app passes in.
3. **Made wrong guesses cost the same** in `update_score`. "Too High" and
   "Too Low" now both subtract 5 points.
4. **Fixed the win payout** by removing the `+ 1` from the formula, so it is
   now `100 - 10 * attempt_number` with a minimum of 10 points.
5. **Fixed the attempt count** in `app.py` by starting it at 0 instead of 1,
   which matches what the "New Game" button already did. Your first guess is
   now attempt 1 either way.
6. **Refactored the logic** by moving `parse_guess`, `check_guess` and
   `update_score` out of `app.py` and into `logic_utils.py`, then updating
   the import in `app.py`.
7. **Fixed and expanded the tests.** I corrected the three starter tests to
   unpack both return values, then added regression tests for the hint
   direction, the string versus number comparison, the scoring penalty across
   attempts 1 to 6, and the win payout ladder including the minimum. All 24
   tests pass.

## 📸 Demo Walkthrough

Here is a full sample game from start to finish, so you can see how the fixed
game behaves without having to run it. This game is on **Normal** difficulty
(range 1 to 100, 8 attempts allowed) and the secret number is **63**.

1. **Start.** The app opens with a score of 0 and 0 attempts used. Opening the
   "Developer Debug Info" expander shows the secret number is 63.
2. **Guess 1: the user enters `40`.** 40 is lower than 63, so the game returns
   **"Too Low"** and shows the hint *"📈 Go HIGHER!"*. The hint now points
   toward the answer instead of away from it. Score goes from 0 to **-5**.
3. **Guess 2: the user enters `70`.** 70 is higher than 63, so the game returns
   **"Too High"** and shows *"📉 Go LOWER!"*. Score goes from -5 to **-10**.
   A wrong guess costs 5 points no matter which direction you missed by, so
   this behaves the same as the guess before it.
4. **Guess 3: the user enters `63`.** This matches the secret, so the game
   returns **"Win"** and shows *"🎉 Correct!"*. Balloons appear. Winning on
   attempt 3 is worth 70 points, so the score goes from -10 to **60**.
5. **Game ends.** A success message shows *"You won! The secret was 63. Final
   score: 60"*. The game status is now "won", so further guesses are blocked
   with *"You already won. Start a new game to play again."*

**Score summary for this game:**

| Attempt | Guess | Outcome  | Hint shown    | Points | Score |
| ------- | ----- | -------- | ------------- | ------ | ----- |
| 1       | 40    | Too Low  | 📈 Go HIGHER! | -5     | -5    |
| 2       | 70    | Too High | 📉 Go LOWER!  | -5     | -10   |
| 3       | 63    | Win      | 🎉 Correct!   | +70    | 60    |

A few behaviors worth pointing out:

- **Hints point the right way.** Before the fix, a guess of 40 against a secret
  of 63 said "Go LOWER!", which sent you further from the answer every turn.
- **Wrong guesses always cost the same.** Both "Too High" and "Too Low" take
  away 5 points. Before the fix, a too-high guess on an even attempt *added*
  5 points instead.
- **The win payout is worth 100 minus 10 per attempt used.** Winning on
  attempt 1 pays 90, attempt 2 pays 80, attempt 3 pays 70, and so on, with a
  minimum of 10 for a long game. Before the fix, your first guess was counted
  twice, so a first-try win only paid 70.
- **Invalid input** such as `abc` is rejected with *"That is not a number."*
  instead of crashing the app.

**Screenshot** *(optional)*: <!-- Insert a screenshot of your fixed, winning game here -->

## 🧪 Test Results

```
# Paste your pytest output here, e.g.:
# pytest tests/
# ========================= X passed in 0.XXs =========================
```

## 🚀 Stretch Features

- [ ] [If you choose to complete Challenge 4, describe the Enhanced UI changes here — a screenshot is optional]
