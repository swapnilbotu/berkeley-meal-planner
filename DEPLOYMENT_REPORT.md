# Deployment report — October 22, 2026

**Status: deployed, enabled, and end-to-end tested with two successful GitHub-hosted Google Tasks write runs.**

Private repository: https://github.com/swapnilbotu/berkeley-meal-planner (default branch `main`, verified private). Standalone Google OAuth authorization is complete, with three encrypted Actions secrets configured. Both hosted write runs refreshed Google access, retrieved the current official menu, updated the existing two meal tasks, and verified their contents. The second run retained both task IDs and created no duplicates. Daily scheduling is enabled. No paid billing or paid usage was enabled.

| Requested step | Verified result |
|---|---|
| Investigate Berkeley menu and clickable nutrition | Complete: traced `cald_filter_xml` and `get_recipe_details` from official UI JavaScript, discovered public XML exports, and matched selected foods to popup responses. |
| Python implementation | Written, with direct official-source retrieval, constrained meal selection, policy checks, Google OAuth/Tasks client, and secure setup script. |
| Automated tests | 36 tests passed locally and in all three hosted runs; 3.79 seconds and 1.93 seconds in the two write runs. |
| Current live menu retrieval | Passed: October 22, 330 recipes across four source files; all six selected food panels verified. |
| Monsoon rule live test | Passed against October 23's published menu: all six specified bowl components, 581.35 kcal and 30.80 g protein; nine selected food panels checked across lunch and dinner. No future tasks written. |
| Weekend live test | Passed against October 24's published menu: 281 recipes from two dining-hall exports; Café 3 lunch and Crossroads dinner; six selected panels verified. No future tasks written. |
| Today's Google Tasks | Both GitHub-hosted write runs updated the existing lunch and dinner using standalone OAuth. Independent connector read-back confirmed exactly two meal tasks, stable IDs and notes, reconciled item totals, October 22 date-only deadlines, and unchanged unrelated tasks. |
| Private repository | Created and verified private under `swapnilbotu/berkeley-meal-planner`. |
| Secure production OAuth | User screenshot confirmed External / In production. Local authorization script configured GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN in encrypted Actions secrets at 20:53 UTC. Both hosted refresh-token exchanges and Google Tasks operations succeeded. No credentials committed or printed. |
| Daily 7 AM schedule | Registered workflow ID `393303938`, verified `active`; YAML uses `timezone: America/Los_Angeles`. Both `GOOGLE_OAUTH_READY=true` and `ZERO_COST_VERIFIED=true` are configured and read back. Next scheduled trigger: October 23, 2026 at 7 AM Pacific; daylight saving changes handled by the timezone field. |
| Zero-cost enforcement | Verified GitHub Free, October Actions usage query initially empty, and signed-in Budgets page showing account-wide Actions $0/$0 with `Usage blocked`. `ZERO_COST_VERIFIED=true` is configured. No budget or billing settings were changed. Standard Ubuntu runner only; no cache/artifact uploads. |
| Hosted execution | Live dry run [39845012641](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39845012641) passed on commit `8e8b569757f82c4245e2bee955e6b90a0497bad4`: 330 recipes, four XML sources, six selected panels verified, correct two-meal totals. Hosted write runs [39852855303](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39852855303) and [39852984641](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39852984641) both passed on commit `a35fff6369124774237e39396ec7c5772dedbd7c`. Each verified exactly two meal tasks after updating them. |
| Older ChatGPT automation | `Daily Berkeley Meal Tasks` was rechecked after authorization and confirmed disabled; no replacement ChatGPT prompt/reminder was created. |

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

The actual GitHub runner, dependency installation, all 36 automated tests, current Berkeley retrieval, selected-panel validation, and execution summary passed in run 39845012641 (20:00:13–20:00:54 UTC on October 22). The production OAuth refresh, actual Google Tasks HTTP client, and GitHub secret configuration then passed in write runs 39852855303 (20:54:34–20:54:54 UTC) and 39852984641 (20:55:28–20:55:44 UTC). Each retrieved 330 recipes, verified six nutrition panels, and logged exactly two meal tasks after writes. Independent read-back showed identical notes and IDs across reruns, and unchanged unrelated tasks. The workflow is active and both configuration gates are enabled. These were manual dispatches of the production workflow; the first scheduled 7 AM invocation has not occurred yet.

## Remaining constraints

- Golden Bear Café is excluded until exact one-swipe combination rules are verified from an official source. Its general acceptance of swipes is confirmed, but arbitrary item combinations are not assumed eligible.
- Google Tasks cannot atomically commit both tasks; network outages can interrupt a run. Reruns reconcile by date and meal slot. Multiple ambiguous legacy duplicates stop for review.
- Closed dining halls, unpublished menus, changed website formats, or missing nutrition produce a visible failure rather than fabricated meals. Therefore daily two-meal delivery cannot be guaranteed during source outages or closures.
- A 7 AM GitHub schedule accounts for daylight saving time, but GitHub may delay or drop scheduled jobs under load.
- Snack macros and dietary details remain explicitly labeled assumptions until the specific wrappers are verified.

## Final configuration and maintenance

- Private application repository: https://github.com/swapnilbotu/berkeley-meal-planner
- Workflow: https://github.com/swapnilbotu/berkeley-meal-planner/actions/workflows/daily-meals.yml
- Schedule: `0 7 * * *` with `timezone: America/Los_Angeles`.
- Both Actions variables are `true`; all three required encrypted secrets exist.
- A separate public, documentation-only site supplies Google consent homepage and privacy URLs: https://swapnilbotu.github.io/berkeley-meal-planner-info/. It contains no credentials or private application code and uses free public GitHub Pages.
- No further user setup is required for ordinary daily operation. The laptop can be off.
- Keep the account-wide $0 Actions spending block in place. If free minutes run out, runs must stop rather than incur charges.
- If Google revokes authorization, rerun the local authorization script. If a menu or service changes, inspect the failed workflow log; do not replace missing official values with invented numbers.
