# Evaluation Results

Model: `qwen2.5-coder:3b` | Runs: 10 | Date: 2026-11-16 22:00

| Metric | Value |
|---|---|
| Fix rate (tests pass at the end) | 20% |
| Diagnosis recall (known buggy functions found) | 90% |
| Diagnosis precision (pointed-to functions that were buggy) | 93% |
| Mean attempts used | 2.60 |
| Patches blocked by guardrails | 6 |
| Runs with changes outside declared targets | 0 |

| Example | Status | Before | After | Recall | Attempts | Seconds |
|---|---|---|---|---|---|---|
| number_guessing_game | Partially fixed | 11 passed, 17 failed in 0.39s | 12 passed, 16 failed in 0.53s | 75% | 3 | 351.6 |
| number_guessing_game | Partially fixed | 11 passed, 17 failed in 0.47s | 12 passed, 16 failed in 0.47s | 75% | 3 | 285.0 |
| grade_calculator | Fixed | 3 passed, 6 failed in 0.51s | 9 passed in 0.48s | 100% | 1 | 91.2 |
| grade_calculator | Fixed | 3 passed, 6 failed in 0.51s | 9 passed in 0.44s | 100% | 1 | 74.3 |
| shopping_cart | Partially fixed | 2 passed, 2 failed in 0.35s | 3 passed, 1 failed in 0.45s | 100% | 3 | 144.3 |
| shopping_cart | Partially fixed | 2 passed, 2 failed in 0.38s | 3 passed, 1 failed in 0.43s | 100% | 3 | 137.3 |
| temperature_converter | Partially fixed | 1 passed, 3 failed in 0.37s | 3 passed, 1 failed in 0.43s | 100% | 3 | 178.3 |
| temperature_converter | Partially fixed | 1 passed, 3 failed in 0.35s | 3 passed, 1 failed in 0.44s | 100% | 3 | 171.7 |
| word_stats | Partially fixed | 1 passed, 3 failed in 0.42s | 2 passed, 2 failed in 0.85s | 100% | 3 | 184.4 |
| word_stats | Partially fixed | 1 passed, 3 failed in 0.39s | 2 passed, 2 failed in 0.36s | 50% | 3 | 163.4 |

| AI confidence | Runs | Fix rate |
|---|---|---|
| high | 10 | 20% |

| Example | Same status across runs | Same location across runs |
|---|---|---|
| number_guessing_game | 100% | 100% |
| grade_calculator | 100% | 100% |
| shopping_cart | 100% | 100% |
| temperature_converter | 100% | 100% |
| word_stats | 100% | 50% |
