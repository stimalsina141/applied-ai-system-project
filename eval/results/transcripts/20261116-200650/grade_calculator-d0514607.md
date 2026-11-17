# Transcript: Grade calculator (session d0514607)

## Explanation shown to the learner

The letter_grade function checks if the score is greater than 90 to return 'A'. However, the condition score > 90 is exclusive, meaning it does not include 90. This means that a score of 90 is not correctly identified as an 'A'. The class_average function calculates the average by summing all the scores and dividing by the number of scores. However, it does not correctly sum the scores because it starts the loop from index 1, which means it does not include the first score in the sum. This results in an incorrect average.

```python
def letter_grade(score):
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    return 'F'
```

## Attempt 1: Fix the letter_grade function to correctly identify 'A' for scores of 90 and above, and correct the class_average function to sum all scores and divide by the number of scores.

```diff
--- a/grades.py
+++ b/grades.py
@@ -1,19 +1,15 @@
 def letter_grade(score):
-    """Turn a 0-100 score into a letter. 90 and above is an A."""
-    if score > 90:
-        return "A"
-    elif score > 80:
-        return "B"
-    elif score > 70:
-        return "C"
-    elif score > 60:
-        return "D"
-    return "F"
+    if score >= 90:
+        return 'A'
+    elif score >= 80:
+        return 'B'
+    elif score >= 70:
+        return 'C'
+    elif score >= 60:
+        return 'D'
+    return 'F'
 
 
 def class_average(scores):
-    """Return the average of a list of scores."""
-    total = 0
-    for i in range(1, len(scores)):
-        total += scores[i]
+    total = sum(scores)
     return total / len(scores)
```

Tests: 9 passed in 0.48s (kept: all tests pass)

# Debugging Report

**Status:** Fixed
**Why it stopped:** All tests pass.
**Attempts used:** 1 of 3

## Problem

A student who scored exactly 90 got a B instead of an A, and the class average comes out lower than it should.

## Root cause

The letter_grade function has a logical error in the condition for returning 'A'. The condition score > 90 is not inclusive, so a score of 90 is not correctly identified as an 'A'. The class_average function is also incorrect because it does not correctly sum the scores and divide by the number of scores.

Confidence: high

- **Confirmed** `grades.py` `letter_grade` (lines 3-11): The letter_grade function incorrectly returns 'B' for a score of 90.
- **Confirmed** `grades.py` `class_average` (lines 13-19): The class_average function incorrectly calculates the average of a list of scores.

## Changes made

- **Attempt 1** (`grades.py` `letter_grade`, `grades.py` `class_average`): The letter_grade function was corrected to return 'A' for scores of 90 and above, and the class_average function was corrected to sum all scores and divide by the number of scores.
  - Assumption: The input to the functions is valid and contains only numbers.

## Validation

- Before: 3 passed, 6 failed in 0.51s
- After: 9 passed in 0.48s

| Check | Result |
|---|---|
| Original bug addressed | 6 of 6 failing tests now pass |
| Existing tests preserved | 3 of 3 still pass |
| Full test suite | 9 passed in 0.48s |
| Unrelated behavior changed | Not detected |

## Concept learned

Understood the importance of using `>=` instead of `>` in conditional statements to handle boundary cases correctly.

## Code quality

No issues found.

Suggested tests:
- test_letter_grade_95
- test_letter_grade_89
- test_letter_grade_80
- test_letter_grade_70
- test_letter_grade_60
- test_letter_grade_59

## Remaining concerns

None identified.
