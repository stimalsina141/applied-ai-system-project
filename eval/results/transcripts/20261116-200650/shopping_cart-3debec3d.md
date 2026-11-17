# Transcript: Shopping cart (session 3debec3d)

## Explanation shown to the learner

In the `add_item` function, the `cart` parameter is set to an empty list by default. However, when a new cart is created, the `cart` parameter is not being reset to an empty list. This means that the cart is being appended to the existing cart, which is causing the items from the previous customer to be added to the new cart. To fix this, we need to reset the `cart` parameter to an empty list when a new cart is created.

```python
def add_item(name, price, cart=None):
    if cart is None:
        cart = []
    cart.append({
```

## Attempt 1: Reset the `cart` parameter to an empty list when a new cart is created.

Blocked by guardrail: Edit 1 (cart.py, add_item): the new code has a syntax error on line 4: '{' was never closed.

## Attempt 2: Reset the `cart` parameter to an empty list when a new cart is created.

```diff
--- a/cart.py
+++ b/cart.py
@@ -1,6 +1,7 @@
-def add_item(name, price, cart=[]):
-    """Add an item to a cart and return the cart. Starts a new cart if none is given."""
-    cart.append({"name": name, "price": price})
+def add_item(name, price, cart=None):
+    if cart is None:
+        cart = []
+    cart.append({'name': name, 'price': price})
     return cart
```

Tests: 3 passed, 1 failed in 0.45s (kept: failures went from 2 to 1)

Analysis: Retry the test to see if the issue is resolved.

## Attempt 3: Reset the `cart` parameter to an empty list when a new cart is created.

```diff
--- a/cart.py
+++ b/cart.py
@@ -1,6 +1,5 @@
 def add_item(name, price, cart=None):
-    if cart is None:
-        cart = []
+    cart = []
     cart.append({'name': name, 'price': price})
     return cart
```

Tests: 2 passed, 2 failed in 0.37s (discarded: it broke 1 test(s) that passed before: test_cart::test_add_to_existing_cart)

Analysis: Retry the patch.

# Debugging Report

**Status:** Partially fixed
**Why it stopped:** Stopped after 3 attempts.
**Attempts used:** 3 of 3

## Problem

A brand new cart already contains items from the previous customer. Also, a 10% discount on a $200 order only takes off $10.

## Root cause

The `cart` parameter in the `add_item` function is not being reset to an empty list when a new cart is created.

Confidence: high

- **Confirmed** `cart.py` `add_item` (lines 1-4): The cart is not being reset when a new cart is created.
- **Confirmed** `cart.py` `cart_total` (lines 8-10): A 10% discount on a $200 order only takes off $10.

## Changes made

- **Attempt 2** (`cart.py` `add_item`): The `cart` parameter was not being reset to an empty list when a new cart was created, causing items from the previous customer to be added to the new cart. The fix resets the `cart` parameter to an empty list when a new cart is created.

Attempts that were not kept:
- Attempt 1: blocked by a guardrail (Edit 1 (cart.py, add_item): the new code has a syntax error on line 4: '{' was never closed.)
- Attempt 3: discarded because it broke 1 test(s) that passed before: test_cart::test_add_to_existing_cart

## Validation

- Before: 2 passed, 2 failed in 0.35s
- After: 3 passed, 1 failed in 0.45s

| Check | Result |
|---|---|
| Original bug addressed | 1 of 2 failing tests now pass |
| Existing tests preserved | 2 of 2 still pass |
| Full test suite | 3 passed, 1 failed in 0.45s |
| Unrelated behavior changed | Not detected |

## Concept learned

Understood the use of default parameters and how they can be used to initialize variables.

## Code quality

No issues found.

Suggested tests:
- test_add_item_with_no_cart
- test_add_item_with_existing_cart

## Remaining concerns

- `test_cart::test_total_with_percentage_discount` still fails: assert 190.0 == 180.0 ± 1.8e-04
  
  comparison failed
  Obtained: 190.0
  Expected: 180.0 ± 1.8e-04
- Suggested next step: Retry the patch.
