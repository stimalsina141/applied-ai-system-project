# Model Card: AI Debugging Coach

## System overview

| | |
|---|---|
| **What it does** | Helps beginner Python programmers understand, fix and verify bugs: diagnosis, plain-language explanation, a small patch, sandboxed tests, up to 3 repair attempts, and a report |
| **AI model** | `qwen2.5-coder:3b`, an open-weight coding model run locally and for free through Ollama. Optional: the paid Claude API (`COACH_PROVIDER=claude`), not used for any results here |
| **What the AI decides** | Its diagnosis, explanation, proposed patch, and failure analysis |
| **What the AI does *not* decide** | Whether a patch is applied (guardrails plus learner approval), whether it is kept (test results), and the final status (test results) |
| **Intended users** | Students learning Python, working on small programs (≤ 10 files) that they wrote themselves |
| **Not intended for** | Production code, large repositories, security-sensitive code, or code from untrusted sources |

## Limitations and biases

**The model is much better at finding bugs than fixing them.** In my
evaluation (5 example projects × 2 runs), it pointed at the right functions
90% of the time, but only 2 of 10 runs ended with all tests passing. It
usually fixes one bug per session. On a project with several bugs, like the
Project 1 number guessing game, it leaves most of them unfixed.

**Its explanations can be wrong while its code is right.** The temperature
converter explanation contradicted itself, but its patch was correct. The
word counter explanation claimed Python "tries to convert them to the same
type" when adding a string and an integer, which is false. For a beginner,
a confident wrong explanation may be worse than none, because the passing
tests make it look trustworthy.

**Follow-up answers are not verified.** Patches are checked by tests, but the
follow-up chat is not. In hands-on testing, asked "What if the list contains
None?", the model answered that `sum()` returns 0; in reality it raises a
`TypeError`.

**It is overconfident.** It rated its confidence "high" and labeled every
finding "Confirmed" in all 10 runs, including one finding that was simply
wrong. The *confirmed / likely / unknown* labels were meant to help learners
calibrate their trust. With this model they carry no information.

**"Fixed" only means "the tests pass."** The coach is only as good as the
tests it is given. A patch that special-cases the test inputs would be marked
Fixed. Without tests, the coach can only say "not verified."

**Style bias.** The model rewrites functions in its own style. It deleted
docstrings and switched `"A"` to `'A'` in code it fixed. That pushes
beginners toward one style and removes their documentation, even when their
original style was fine.

**Who can use it.** The free local model needs a computer with about 8 GB of
RAM. On my 8 GB laptop the larger 7B model was too slow to use at all. The
better-quality option (the Claude API) costs money. So the quality of help a
student gets depends on their hardware or their budget. It only supports
Python, and its explanations are in English.

## Future improvements

- **A stronger free model.** On a computer with 16 GB of RAM,
  `qwen2.5-coder:7b` can be picked in the sidebar. Re-running the evaluation
  with it would show how much of the 20% fix rate is the model and how much
  is the design.
- **Better retry feedback.** The failure analysis often says just "Retry the
  patch." Feeding the exact failing assertion back to the fixer, instead of
  relying on the model's summary, should make attempts 2 and 3 more useful.
- **Fix one function per attempt.** The model does best with one bug at a
  time. On multi-bug projects, the coach could target the function with the
  most failing tests first.
- **Check the explanation, not just the code.** For example, ask the model
  to predict a failing test's output from its explanation, and compare that
  to the real output.
- **A "hints only" mode** that never shows a patch, for learners who want to
  fix the bug themselves.
- **A real sandbox** (a container with no network) so untrusted code can be
  run safely.
- **Verify follow-up answers** by running small snippets the answer makes
  claims about (for example `sum([None])`) before showing it.

## Misuse and prevention

| Possible misuse | How the system limits it | What remains |
|---|---|---|
| **Getting homework fixed without learning** | The workflow is explanation first, then the learner reads and approves each diff, and the report centers on the concept learned | The small model often puts the fixed code in its explanation anyway, so the app now hides code examples until the fix is tested. It can still describe the fix in words ("change `-` to `+`"). A "hints only" mode that withholds patches would help |
| **Running harmful code on someone's machine** | Only `python -m pytest` with fixed arguments runs, never a shell. Tests run on a temporary copy with a 30 s timeout, and API keys are removed from the environment | The temporary folder is not a security sandbox; the code can still reach the file system and network. The coach should only run code you wrote or trust, and the README says so |
| **Prompt injection** (instructions hidden in code comments or test output) | The system prompt treats code, tests and output as data. The AI cannot run anything itself; a hijacked answer can only produce a bad patch, which still has to pass the guardrails, the learner's review and the tests | A convincing but wrong *explanation* could still mislead a learner |
| **The AI "cheating" by editing the tests** | Test files are protected, and a patch can only replace the functions it declared | None found in testing |
| **Leaking private code** | By default the model runs locally, so no code leaves the computer. Logs record counts and file names, never source code | With the optional Claude provider, code is sent to Anthropic's API |

## What surprised me while testing reliability

1. **The gap between diagnosing and fixing.** I expected that a model that
   finds 90% of the buggy functions would fix most of them. It fixed all the
   tests in only 20% of runs. Pointing at the right place and writing a
   correct change turned out to be very different skills.

2. **The confidence scores were useless.** I built a "fix rate by
   confidence" metric expecting high-confidence runs to succeed more. Every
   run said "high", so the metric had nothing to compare.

3. **My own guardrail blocked every fix at first.** In my first design, the AI
   had to copy the exact text it wanted to replace. The small model kept
   writing `'Words: '` where the file said `"Words: "`, and all 3 attempts
   were rejected. The guardrail was correct, but the design didn't fit the
   model. I switched to having the model rewrite a whole declared function,
   which the app locates with Python's parser.

4. **The checks around the AI did a lot of the work.** Guardrails blocked 6
   broken patches (syntax errors, malformed functions) before they ran. In
   the shopping cart example, the keep/discard rule threw away an attempt
   that broke a passing test and kept the earlier correct fix. No run changed
   code outside its declared functions.

5. **Reading transcripts found problems the numbers didn't.** The temperature
   converter run "improved 2 tests" on paper, but its explanation contradicted
   itself. Without the human review table I would never have seen it.

6. **Using the app myself found what automated tests didn't.** In one
   hands-on session with a simple `average([])` crash, every automated check
   passed, but I found six problems a learner would notice: the fix was given
   away before I asked for it, the report said "Not detected" when it only
   meant "not detected by my two tests", and returning 0 for an empty list
   was presented as the only answer when it was really a choice my test made.

7. **One sentence in the prompt flipped the results.** To fix the root-cause
   wording, I added a rule asking for explanations in terms of what Python
   does. The `average` explanation got better, but the grade calculator,
   which had been fixed in every run, started failing every run, while
   `is_even` went the other way. I reverted the rule, because the evaluation
   numbers were measured without it. A small model at temperature 0 is very
   sensitive to wording, which is why prompt changes need the full
   evaluation, not one manual check.

8. **Retries often repeated the same idea.** The failure analysis frequently
   said only "Retry the patch," which gave the next attempt nothing new, so
   attempts 2 and 3 often produced the same result.

## Collaboration with AI

I built this project with Claude Code, an AI coding assistant, as a
collaborator. I described the features I wanted and made the decisions, and
it proposed designs, wrote most of the code and tests, and ran them. I
reviewed what it produced, tested it, and pushed back when something didn't
fit. In a way, building a tool where an AI proposes and code verifies matched
how I worked with the AI: it proposed, and I checked.

### A suggestion I accepted: rewrite whole functions instead of copying text

After the first real run failed on every attempt, the assistant ran a small
experiment showing that the local model was much better at writing a
complete function than at copying exact lines. It suggested changing the
patch format so each edit is the full new version of one declared function,
which the app swaps in using Python's `ast` parser. I accepted it because the
evidence was concrete (0 of 3 attempts worked before; the next run kept a
real fix), and because it made the guardrail *stronger*: an edit now
physically cannot touch code outside its function. The trade-off, which I
documented, is that the model can also rewrite lines it shouldn't, like
docstrings. The diff preview shows that, and the learner can reject it.

### A suggestion I did not accept: the paid Claude API

The assistant's original design used Anthropic's most capable model through
the paid Claude API. It explained how to get an API key and estimated that a
full evaluation would cost about $5–10. I rejected it. This is a student
project, nobody is paying me for it, and I wasn't going to pay to run it. I
also wanted anyone who clones the repo to be able to run it without an
account. The suggestion wasn't wrong; Claude would almost certainly fix more
bugs than a 3B local model. But it was a poor fit for my constraints. I asked
for a free option, and we switched the default to a local model through
Ollama, keeping Claude only as an optional setting. The cost of that choice
shows clearly in the 20% fix rate, and I think being honest about that
trade-off matters more than a better number.

I also changed *how* we worked: the assistant planned to build everything
and commit once at the end, and I asked for commit checkpoints along the way
with suggested commit messages, so I could review and commit each piece
myself.
