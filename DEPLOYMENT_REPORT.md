# Deployment report — October 24, 2026

Private repository: https://github.com/swapnilbotu/berkeley-meal-planner

## Current status

**Deployed, enabled, and verified.** Both the service's test request and an actual
scheduled trigger produced successful GitHub runs. Each passed 50 tests and read
back exactly two meal tasks without changes or duplicates. The final daily schedule
is saved and enabled. No paid billing or paid usage has been enabled.

The schedule change is deployed on `main` in commit
[`13bd585`](https://github.com/swapnilbotu/berkeley-meal-planner/commit/13bd58563485c5a46de3c8863dab44f081424159).

GitHub's native cron did not deliver the morning target on October 23 or 24.
October 23's first recorded scheduled event was at 11 AM Pacific. No scheduled
run existed at the October 24 morning checks. Manual dispatch worked. These
observations do not establish GitHub's internal cause.

The replacement scheduling path is cron-job.org → GitHub workflow dispatch →
Python → Google Tasks. This is an independent deployed service, not a ChatGPT
scheduled prompt. Google OAuth credentials remain in encrypted Actions secrets.

## Configuration

- Free scheduler job: the job in your private cron-job.org dashboard
- Production schedule: `0,15 7 * * *`, timezone `America/Los_Angeles`.
- Primary attempt: 7:00 AM; recovery check: 7:15 AM; daylight saving handled by timezone.
- Native GitHub fallback: `17 16 * * *` (9:17 AM PDT / 8:17 AM PST).
- Workflow: https://github.com/swapnilbotu/berkeley-meal-planner/actions/workflows/daily-meals.yml
- External request: POST workflow `393303938` on `main`, with
  `write_tasks=true` and `recovery_only=true`.
- Single-writer concurrency and date/meal matching prevent duplicate normal reruns.
  Completed tasks remain completed. Ambiguous duplicates stop for review.
- `ZERO_COST_VERIFIED=true` and `GOOGLE_OAUTH_READY=true` remain the runner gates.
- Standard Ubuntu runner, eight-minute job cap, no cache or artifact uploads.
- At three automatic attempts/day, 31 days gives 93 runs and 744 job minutes at
  the cap, before setup, rounding, manual tests, and other repositories' usage.
- The account-wide Actions $0 stop-spending block was verified October 22.
  Do not enable a paid allowance; exhausted free minutes must stop execution.

## Verification evidence

| Check | Evidence |
|---|---|
| Current official menu and actual Tasks writes | [Run 40108915300](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/40108915300): 45 tests, 285 official recipes from two dining-hall XML files, six selected nutrition popups verified, two October 24 meal tasks created and read back. |
| Recovery behavior | [Run 40109403696](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/40109403696): 50 tests passed; exactly two existing tasks verified, no changes. |
| Authenticated external test request | cron-job.org HTTP 200, [run 40112697565](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/40112697565), October 24 at 9:41 AM Pacific: 50 tests passed; exactly two existing tasks verified, no changes. |
| Genuine timed service execution | Fired October 24 at 9:45:04 AM Pacific for the temporary 9:45 AM test, reported 4.98 seconds jitter and HTTP 200; started [run 40113002748](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/40113002748). Succeeded: 50 tests passed; at 9:45:34 AM the log verified exactly two existing tasks with no changes. GitHub reported completion later, around 9:53 AM. |
| Final saved schedule and workflow | Enabled job reloaded and verified: `0,15 7 * * *`, America/Los_Angeles, next runs October 25 at 7:00 and 7:15 AM. Temporary test schedule removed. GitHub workflow ID 393303938 is active; main contains only the single later native fallback. |
| Independent Tasks check | Existing My Tasks list for the configured Google account: exactly one lunch and one dinner due October 24; both already completed. IDs and full notes retained. |
| Local regression suite | All 50 tests passed after preparing the workflow schedule change. |
| Older ChatGPT meal automation | Daily Berkeley Meal Tasks remains disabled; no replacement ChatGPT meal prompt was created. |

Today's task IDs:

- Lunch: `dlZ1S0JJQkM4ZHQxVlZaQw`
- Dinner: `VW5ZTUZyRWUzV2JIdm9YMA`
- Existing My Tasks list: `MEAL_TASKS_LIST_ID`

| Meal | Location | Calories | Protein |
|---|---|---:|---:|
| Spinach Tofu Tomato Scramble + Split Pea Soup + Vegan Wellness Stew | Crossroads | 570.44 | 44.27 g |
| Cheese Pizza + Paprika Rosemary Tofu + Sauteed Pinto Beans with Green Chili | Crossroads | 611.16 | 32.21 g |

Meals total 1,181.60 kcal and 76.48 g protein, using two swipes. User-supplied snack
estimates add 570 kcal and 33.5–34.5 g protein: one protein bar and 1.25 usual
trail-mix portions. Estimated day total: 1,751.60 kcal and 109.98–110.98 g protein.
The snack values are estimates; meal values are verified official recipe values
scaled by serving count. Due values encode October 24 as a date, not a clock time.

## Maintenance and limits

The scheduler's repository-limited GitHub token expires **November 23, 2026 at
9:34 AM Pacific (17:34:05 UTC)**, verified from GitHub's response header. Renew it
before that date and update the Authorization value directly in cron-job.org;
never send the token in chat or commit it. This does not require reauthorizing
Google Tasks. See [scheduler instructions](docs/external-scheduler.md).

Scheduling at 7 AM starts execution; it does not promise task delivery at exactly
7:00:00. The external timer avoids GitHub's cron dispatcher, but available GitHub
runners, Berkeley menus, and Google Tasks are still dependencies. Missing official
nutrition or availability fails visibly rather than inventing a meal. Google
Tasks has no two-task transaction; recovery repairs an interrupted partial write.

Dining halls remain limited to Crossroads and Café 3, with Crossroads preferred
when daily macros are comparable. The weekday Monsoon rule, weekend restrictions,
vegetarian/no-egg days, compact notes, and one-swipe eligibility checks are unchanged.
Golden Bear Café stays excluded until exact official one-swipe combinations are
verified. Snack ingredient/package verification remains a separate limitation.

Initial deployment evidence is retained in [run 39852855303](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39852855303)
and [run 39852984641](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39852984641):
both October 22 hosted writes passed, verified official nutrition, and retained
stable task IDs without duplicates. The application repository remains private.
