# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the hints were backwards").
  - The setup looked decent at the first glance but the logic of the game made it clear there were plenty of bugs.
  - The hints of each game were very misleading and completely wrong.
  - The range for "easy" and "hard" is determined for each game, for example: for easy it is from 1-20, but the secret number was 98.
  - The "New Game" button didn't work properly. I had to refresh every time to start a new game.
  - The attempts allowed were also faulty. The first attempt was not counted in any game played.
  - The scores after each game was also not correct.

**Bug Reproduction Log**

Document at least 3 bugs you found. Add rows as needed.

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
| ----- | ----------------- | --------------- | ---------------------- |
| 20    | Go HIGHER!        | Go LOWER!       | none                   |
| 93    | Go LOWER!         | Go HIGHER!      | none                   |
| 77    | Go HIGHER!        | Go LOWER!       | none                   |

---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
  - I used Claude Code in agent mode inside VS Code. I used it to move the game logic out of `app.py` into `logic_utils.py`, to help fix the scoring, and to write some tests.

- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
  - **What the AI suggested:** While moving `update_score` over, it caught something I had missed. If you guessed too high, the code gave you 5 points instead of taking 5 away, but only on even numbered attempts. Guessing too low always took 5 away. So sometimes a wrong guess made your score go up. It said both should just take 5 away, since a wrong guess is a wrong guess either way.
  - **Was it correct?** Yes. Once I looked at the old code I could see the two were never supposed to be different.
  - **How I verified it:** I wrote tests that check both "Too High" and "Too Low" take away exactly 5, and I ran them for attempts 1 through 6 instead of just one number, since the bug only showed up on even ones. Then I copied the old broken version into a scratch file and ran the same tests on it. It failed on attempts 2, 4 and 6, which told me my test was really catching the bug and not just passing by luck. All 24 tests pass now.

- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).
  - **What the AI suggested:** When the agent moved `update_score` into `logic_utils.py`, it fixed the too high / too low part but left the winning score alone, and then told me the win part was "untouched" like that meant it was fine. I almost took its word for it and moved on, since it had just been right about the other bug.
  - **Was it correct?** No, it was misleading. The winning score was `100 - 10 * (attempt_number + 1)`, and that `+ 1` charged you for one more guess than you actually used. On top of that, `app.py` added 1 to the attempt count _before_ it worked out your score, so you got charged twice for the same guess. Winning on your very first try only gave you 70 points instead of 90. The agent was not wrong about what it changed, it just made it sound like the rest of the function had been checked when it had not been.
  - **How I verified it:** I called `update_score(0, "Win", 1)` myself and got 80, not 90, so the `+ 1` was clearly taking a guess away from me. Then I followed the attempt count through `app.py` and saw it started at 1, but the "New Game" button set it to 0, and either way it got 1 added to it before the score was worked out. So the same first try win paid out 70 if you just opened the page but 80 if you clicked New Game first. That also explains the thing I noticed at the very start, where my first guess never seemed to count.
  - **How I fixed it:** I took the `+ 1` out of the formula so it is now `100 - 10 * attempt_number`, and I changed the starting attempt count in `app.py` from 1 to 0 so it matches what "New Game" already did. Now your first guess really is attempt 1, and winning on it gives you the full 90 either way. I added tests for this too, so winning on attempts 1 to 5 has to pay 90, 80, 70, 60, 50, and a very long game still pays the minimum 10.
  - **What I took from this:** When AI says it did not touch something, that is not the same as saying it checked it. I now go read the parts it skipped instead of assuming they were fine just because it got the other part right.

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
  - I ran pytest after every change instead of just looking at the app and assuming it was better. I ran `python3 -m pytest tests/ -v` and went through the list to see which ones passed and which ones failed. I also did not count a bug as fixed unless I saw it fail first and then pass. For the hint bug I went back to the same guesses from my bug log above and checked that 20 now says "Go HIGHER!" instead of "Go LOWER!". For the scoring bug I ran my new test against the old broken code first to make sure it would have caught it, because if a test passes on the broken version too then it is not really testing anything.

- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
  - I ran pytest on `tests/test_game_logic.py`. One of the tests I added is `test_wrong_guess_always_costs_five`, which checks that both "Too High" and "Too Low" take 5 points away. I ran it for attempts 1 through 6 instead of just picking one number. That mattered, because the bug only happened on even attempts, so if I had only tested attempt 1 it would have passed and I would have thought the code was fine.
  - Running pytest also showed me something I was not even looking for. Three of the starter tests were failing, and it was not because of my changes. They were comparing the whole result to just `"Win"`, but `check_guess` gives back two things, the outcome and the hint message. So the test was comparing `("Win", "🎉 Correct!")` to `"Win"` and failing. I fixed those to pull out just the outcome. My final pytest run came back 24 passed, 0 failed.

- Did AI help you design or understand any tests? How?
  - Yes. I asked it to write a test aimed at the scoring bug specifically, and it suggested running the same test across several attempt numbers instead of one, since the bug depended on whether the attempt was even or odd. I probably would have written one test with one number and moved on. It also suggested running the test against the old broken code to prove the test actually worked, which I liked because it stopped me from trusting a green checkmark too quickly.

---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?
  - Every time you click a button or type something in Streamlit, it runs your whole file again from the top. That means any normal variable is created all over again, so it does not keep its value. Session state is where you put things you want to stay the same between clicks, which is why the app checks `if "secret" not in st.session_state` before picking a number. Without that check the secret would change on every guess and you could never win. The other side of it is that session state keeps things until you clear them yourself, which is why "New Game" did not fully work, it never reset the status so the app still thought I had already won.

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
  - Testing the test itself. Before trusting that a bug was fixed, I ran my new test against the old broken code to make sure it would actually fail. If a test passes on both versions then it is not really checking anything, it just looks like it is. I also want to keep running tests across a few different inputs instead of one, since the scoring bug only showed up on even numbered attempts and one test would have missed it.

- What is one thing you would do differently next time you work with AI on a coding task?
  - I would read the parts the AI says it did not change. When it told me the win scoring was "untouched" I almost moved on, but untouched just means it did not look at it, not that it was fine. Next time I want to give it smaller tasks too, because it is easier to check one change than a big pile of them at once.

- In one or two sentences, describe how this project changed the way you think about AI generated code.
  - I used to think code was probably fine if it ran without errors, but this game ran perfectly and was wrong the whole way through. Now I assume AI code can be confidently wrong, and the parts that look the most careful can be the parts actually hiding the bug.
