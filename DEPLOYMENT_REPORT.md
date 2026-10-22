# Deployment report — October 22, 2026

**Status: private repository deployed and hosted live dry test passed; unattended Google Tasks writes await OAuth authorization.**

Private repository created: https://github.com/swapnilbotu/berkeley-meal-planner (default branch `main`, verified private). GitHub authorization is complete. No standalone Google OAuth refresh token was configured. A GitHub-hosted live dry test passed; scheduled task writes remain gated. No paid billing or paid usage was enabled. A hosted Google Tasks write test has not yet run.

| Requested step | Verified result |
|---|---|
| Investigate Berkeley menu and clickable nutrition | Complete: traced `cald_filter_xml` and `get_recipe_details` from official UI JavaScript, discovered public XML exports, and matched selected foods to popup responses. |
| Python implementation | Written, with direct official-source retrieval, constrained meal selection, policy checks, Google OAuth/Tasks client, and secure setup script. |
| Automated tests | 36 tests passed locally and on GitHub Actions (4.60 seconds on the hosted runner). |
| Current live menu retrieval | Passed: October 22, 330 recipes across four source files; all six selected food panels verified. |
| Monsoon rule live test | Passed against October 23's published menu: all six specified bowl components, 581.35 kcal and 30.80 g protein; nine selected food panels checked across lunch and dinner. No future tasks written. |
| Weekend live test | Passed against October 24's published menu: 281 recipes from two dining-hall exports; Café 3 lunch and Crossroads dinner; six selected panels verified. No future tasks written. |
| Today's Google Tasks | Updated the existing lunch and dinner through the connected Google Tasks account. Read-back confirmed exactly two meal tasks, matching complete generated notes and October 22 date-only deadlines. |
| Private repository | Created and verified private under `swapnilbotu/berkeley-meal-planner`. |
| Secure production OAuth | Blocked: a new standalone grant is required; the available Cloud Browser could not open Google Cloud Console. No credentials exported or committed. |
| Daily 7 AM schedule | Registered workflow ID `393303938`, verified `active`; YAML uses `timezone: America/Los_Angeles`. Scheduled writes require `GOOGLE_OAUTH_READY=true`, which is deliberately unset until authorization. |
| Zero-cost enforcement | Verified GitHub Free, October Actions usage query initially empty, and signed-in Budgets page showing account-wide Actions $0/$0 with `Usage blocked`. `ZERO_COST_VERIFIED=true` is configured. No budget or billing settings were changed. Standard Ubuntu runner only; no cache/artifact uploads. |
| Hosted execution | Live dry run [39845012641](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39845012641) passed on commit `8e8b569757f82c4245e2bee955e6b90a0497bad4`: 330 recipes, four XML sources, six selected panels verified, correct two-meal totals. Hosted OAuth-to-Tasks writing remains untested. |
| Older ChatGPT automation | `Daily Berkeley Meal Tasks` was confirmed disabled; no replacement ChatGPT prompt/reminder was created. |

## Today's verified task results

| Task | Location | Calories | Protein |
|---|---|---:|---:|
| Lunch — Crossroads / Paprika Rosemary Tofu | Crossroads | 602.66 | 32.94 g |
| Dinner — Crossroads / Baked Tofu Piccata | Crossroads | 598.77 | 46.07 g |

Lunch: two published 2 oz servings of paprika rosemary tofu, one 8 oz bean chili, and one 2 oz hummus.

Dinner: 1.5 published 4.52 oz servings of baked tofu piccata, one 5.59 oz sweet-and-sour tofu, and one 3.87 oz green-bean garlic stir fry.

Both use one dining-hall entry, are vegetarian without eggs, and use official published recipe values. Proportional serving arithmetic is stated explicitly. Prepared sauces/oils are included in the recipe totals.

Meal totals: **1,201.43 kcal, 79.01 g protein, two swipes**. With one estimated 170 kcal / 21 g protein bar and 1.25 usual trail-mix portions estimated at 375 kcal / 10 g protein, the day is **1,746.43 kcal and 110.01 g protein**. Snack estimates are not Berkeley facts and package-specific ingredients are unverified.

Existing task IDs retained:

- Lunch: `R0NMTmhsalNhelZ2WENBRQ`
- Dinner: `S0NoMjNUNTU3TzFSX3B6UQ`

Verified list: existing `My Tasks`, ID `MDM4Mzk1Mjg4NzQxODE3ODY0NzU6MDow`, connected account `swapnil_gmail`. Returned due values were `2026-10-22T00:00:00.000Z`, which encode a Google Tasks date, not an assigned clock time. No duplicate meal task was created; unrelated tasks remained unchanged.

## Test scope

Tests cover known official nutrition values; stale menu/food dates; invalid or missing nutrition; explicit closures; XML declaration rejection; vegetarian/no-egg rules; meat/broth exclusions; weekend dining-hall restrictions; exact Monsoon composition; missing-component and missing-policy fallbacks; daily totals; completed/hidden-task updates; pagination; other-date protection; managed duplicate cleanup; ambiguous legacy duplicate preflight; lost insertion response recovery; read-back mismatch; missing OAuth secrets; popup disagreement; and Los Angeles summer/winter dates.

The actual GitHub runner, dependency installation, all 36 automated tests, current Berkeley retrieval, selected-panel validation, and execution summary passed in run 39845012641 (20:00:13–20:00:54 UTC on October 22). The production OAuth refresh, actual Google Tasks HTTP client, and GitHub secret configuration still need live testing. The workflow is registered and active, but scheduled writes remain gated; this is not a completed unattended deployment.

## Remaining constraints

- Golden Bear Café is excluded until exact one-swipe combination rules are verified from an official source. Its general acceptance of swipes is confirmed, but arbitrary item combinations are not assumed eligible.
- Google Tasks cannot atomically commit both tasks; network outages can interrupt a run. Reruns reconcile by date and meal slot. Multiple ambiguous legacy duplicates stop for review.
- Closed dining halls, unpublished menus, changed website formats, or missing nutrition produce a visible failure rather than fabricated meals. Therefore daily two-meal delivery cannot be guaranteed during source outages or closures.
- A 7 AM GitHub schedule accounts for daylight saving time, but GitHub may delay or drop scheduled jobs under load.
- Snack macros and dietary details remain explicitly labeled assumptions until the specific wrappers are verified.

## Unavoidable next authorization steps

1. GitHub connection and private repository creation are complete; no additional GitHub connection is needed.
2. Create/approve a no-billing Google OAuth client and authorize the Tasks scope for `swapnilbotu@gmail.com`; the included script writes its credentials directly to GitHub encrypted secrets.
3. GitHub free allowance and effective $0 stop-spending protection are verified. After the three secrets exist, set `GOOGLE_OAUTH_READY=true`; leave the $0 budget unchanged.

The hosted dry test is complete. After authorization, run the hosted write test, repeat it to prove stable task IDs, confirm scheduled writes are enabled, and replace this report's incomplete status with actual write-run evidence.
