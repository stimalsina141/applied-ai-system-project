# Human Evaluation

A person reviews the coach's outputs against the criteria below. Automated
checks (pytest) can tell whether a fix works. They cannot tell whether an
explanation is accurate and understandable to a beginner, so a person grades
that here.

**How to fill this in:** run `python -m eval.run_eval`, open each transcript
in `eval/results/transcripts/<timestamp>/`, and grade it. Use **Pass**,
**Partial** or **Fail** in the Result column, and add a short note.

## 1. AI output quality (graded by a person)

Model: `qwen2.5-coder:3b` (local, via Ollama). Transcripts:
`eval/results/transcripts/20261116-200650/`.

First-pass grades were drafted with an AI assistant, quoting the transcripts.
Reviewed and confirmed by: _(your name, date)_

| Test input | Evaluation criteria | Result | Notes |
|---|---|---|---|
| Number guessing game: "The secret number changes every time I click Submit..." | Root cause names Streamlit reruns / the secret being regenerated in `init_game`; explanation comes before the fix and defines "rerun" and "session state" | Partial | Says the secret "is being re-initialized every time", which is correct, and patches `init_game` correctly. Never mentions Streamlit reruns or session state, so a beginner learns *what* but not *why*. (`number_guessing_game-6a4aff34.md`) |
| Number guessing game (same run) | Patch is minimal: changes only the buggy functions; New Game resets score, status and history | Partial | The one kept patch touches only `init_game` (+6 −6), but it also deleted the docstring. `new_game` was never diagnosed or fixed. |
| Grade calculator: "exactly 90 got a B" | Identifies `>` vs `>=` as a boundary condition and the loop starting at index 1 as an off-by-one error, in plain words | Pass | Explains that "> 90 is exclusive" and that the loop "starts from index 1… does not include the first score". Fixed in 1 attempt. Fix replaced the loop with `sum()` and dropped the docstrings. (`grade_calculator-bda5065b.md`) |
| Shopping cart: "new cart already has items" | Explains that a default list is created once and shared between calls, and gives a small example | Fail | The fix is right (`cart=None`), but the explanation ("the cart parameter is not being reset") never says the default list is created **once** and shared, which is the actual concept. (`shopping_cart-3debec3d.md`) |
| Word counter: `TypeError` traceback | Uses the traceback line to locate the bug; explains why `str + int` fails | Partial | Locates line 8 correctly, but says "Python tries to convert them to the same type", which is false: Python raises an error instead. (`word_stats-8829634f.md`) |
| Temperature converter: 212°F gives 194.2°C | Explains operator precedence (`*` and `/` before `-`) with the actual numbers | Fail | Contradicts itself ("is subtracting 32 and then multiplying by 5/9, but the correct formula is to subtract 32 and then multiply by 5/9") and never mentions precedence. The patch was still correct. (`temperature_converter-6c940d35.md`) |
| Any run | Findings are honestly labeled: nothing marked "confirmed" without evidence | Fail | Every finding in all 10 runs is "Confirmed" and every confidence is "high". In word_stats, "`word_count` is returning an integer instead of a string" is marked Confirmed but is wrong. |
| Any run | Explanation comes before the fix (no fixed code in the explanation) | Fail | Grade-calculator, shopping-cart, temperature and word-counter explanations all include the fixed code as their "small example". |
| Any run that is not Fixed | The report clearly says what is still broken and suggests a next step | Partial | The report lists every still-failing test with its assertion (computed by the app, not the AI), so that part works. But the AI's suggested next step is often just "Retry the patch." |

## 2. Application behavior (verified by automated tests in `tests/`)

| Test input | Evaluation criteria | Result | Verified by |
|---|---|---|---|
| Empty code box | Handles gracefully with a clear message, no crash | Pass | `test_from_paste_requires_code` |
| File path `../outside.py` or `/etc/passwd.py` | Rejected before anything runs | Pass | `test_unsafe_paths_are_rejected` |
| AI patch edits a test file | Blocked by guardrail, counted as an attempt, coach retries | Pass | `test_guardrail_blocks_edit_to_test_file_and_counts_attempt` |
| AI patch edits outside its declared function | Blocked by guardrail; only the declared function's lines change | Pass | `test_edit_must_be_inside_declared_function`, `test_only_the_declared_function_changes` |
| AI patch has a syntax error | Blocked before running, counted as an attempt | Pass | `test_new_code_with_syntax_error_is_rejected` |
| Ollama not running / model not downloaded | Start button disabled, message says exactly what command to run | Pass | `test_status_when_ollama_not_running`, `test_status_reports_missing_model_and_ready` |
| AI patch fixes one test but breaks another | Patch discarded, original code kept | Pass | `test_patch_that_breaks_passing_test_is_discarded` |
| Code with an infinite loop | Test run stops at the timeout | Pass | `test_infinite_loop_times_out` |
| Test code tries to read `ANTHROPIC_API_KEY` | Key is not visible to test code | Pass | `test_api_keys_are_hidden_from_test_code` |
| Three wrong patches in a row | Stops after 3 attempts with "Unable to fix" | Pass | `test_stops_after_max_attempts` |
| Pasted code with no tests | Status is "not verified", never "Fixed" | Pass | `test_no_tests_means_unverified` |
| AI service fails mid-session (e.g. rate limit) | Session ends cleanly with the reason shown | Pass | `test_ai_service_error_ends_session_cleanly` |
| AI says it needs more information | Stops before patching and shows its questions | Pass | `test_needs_more_info_stops_before_patching` |
| Run automatically toggle on | Skips the approval step, but "Fixed" still comes from a real pytest run | Pass | `test_run_automatically_skips_approval_but_still_runs_tests` |
| Unfixable bug with the slider set to 2 | Stops at "Attempt 2 of 2" with "Unable to fix", never "Fixed" | Pass | `test_unfixable_bug_stops_at_slider_limit` |
| Empty code box / code file named like a test | Clear message, no crash | Pass | `test_bad_input_shows_message_without_crashing` |
| Pasted code with a syntax error | Baseline reports the error, app keeps working | Pass | `test_syntax_error_in_pasted_code_does_not_crash` |
| A successful fix on a built-in example | The example's files on disk are byte-for-byte unchanged | Pass | `test_example_files_on_disk_are_never_modified` |
| Code example that contains the fix | Hidden until the fix is tested; prose shown outside the code block | Pass | `test_review_mode_end_to_end`, `test_split_code_separates_prose_from_code` |
| Report wording | Says "not detected by the N provided tests" instead of claiming nothing changed; notes that test-defined behavior is a choice | Pass | `test_report_does_not_overclaim`, `test_design_choices_are_reported` |

## 3. Hands-on user testing (real model, `qwen2.5-coder:3b`)

I used the app as a learner would. Issues found in the first session were
fixed and then re-tested.

| Test input | Evaluation criteria | Result | Notes |
|---|---|---|---|
| `average([])` with `ZeroDivisionError`, tests require 0 | Full loop works: diagnose, propose, approve, sandbox test, report | Pass | Fixed in 1 attempt; report numbers matched the workflow log |
| Same run, first version of the app | Explanation must not give away the fix | Fail → fixed | The explanation's code example contained the fix (and its prose rendered inside the code block). The app now hides code examples until the fix is tested and separates prose from code |
| Same run, first version of the app | Report must not overclaim | Fail → fixed | "Not detected" / "None identified" now say "by the 2 provided tests" and that untested inputs were not checked |
| Same run, first version of the app | Report should say that returning 0 was a choice | Fail → fixed | The report now has a design-choices note. The model can also list alternatives (None, ValueError), though the 3B model didn't in the re-test |
| Same run, first version of the app | Root cause in Python terms, not "undefined in mathematics" | Fail → fixed | Re-test: "Python raises a ZeroDivisionError when you attempt to divide by zero, and len([]) returns 0" |
| "Max repair attempts" slider | Clear that it's a limit, and whether it applies mid-session | Fail → fixed | Now has a tooltip, is locked during a session, and the sidebar shows "Attempts used: X of N" |
| `is_even` returning `n % 2 == 1`, no traceback | Diagnosis works without an error message; confidence is sensible | Partial | Fixed in 1 attempt, but the explanation was wrong ("uses == instead of %"; the real bug compares to 1 instead of 0), and confidence was "high" |
| `add` with a test that can never pass (`add(2, 3) == 6`), max 2 attempts | Uses all attempts, stops honestly, no claim of success | Pass | "Unable to fix" after 2 of 2. It did not suggest that the test itself might be wrong |
| Follow-up: "What if the list contains None?" | Answer grounded in the code and correct | Fail | Said `sum()` would return 0; actually `sum([None])` raises `TypeError`. Follow-up answers aren't verified by tests, so they can be confidently wrong |
