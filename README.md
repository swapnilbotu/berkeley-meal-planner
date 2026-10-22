# Berkeley meal planner

Deterministic Python planner using official Berkeley menu XML and nutrition-popup requests. No AI inference, paid API, paid hosting, database, or commercial scheduler is used.

**Deployment status: enabled and end-to-end tested on October 22, 2026.** Private repository: https://github.com/swapnilbotu/berkeley-meal-planner. Both GitHub-hosted write runs [39852855303](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39852855303) and [39852984641](https://github.com/swapnilbotu/berkeley-meal-planner/actions/runs/39852984641) passed all 36 tests, retrieved 330 official recipes, cross-checked six selected nutrition panels, and updated exactly two Google Tasks. Independent read-back confirmed stable task IDs, identical notes, no duplicates, and unchanged unrelated tasks. Google OAuth secrets are configured; the daily 7 AM America/Los_Angeles workflow is active with both readiness variables enabled. GitHub's account-wide $0 Actions budget was verified with usage blocked. See `DEPLOYMENT_REPORT.md` for evidence and limitations.

## Run locally

Requires Python 3.12+.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python mealplanner.py
```

The default is a live dry run, with no Google Tasks writes. Output goes to `out/plan.json`, excluded from git. `--date YYYY-MM-DD` supports testing dates published by Berkeley. Write mode only permits today's date in America/Los_Angeles:

```bash
python mealplanner.py --write
```

Write mode reads `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` from the environment. It verifies the authenticated email is `swapnilbotu@gmail.com` and requires the already existing `My Tasks` list with the verified ID in `mealplanner.py`. It never creates a task list.

## Data and meal rules

1. POST `cald_filter_xml` with today's Los Angeles date to the official WordPress AJAX endpoint. This is the request made by the menu date filter.
2. Discover the actual date-specific XML paths from `data-location`, rather than inventing paths or assuming recurring menus.
3. Fetch the four permitted location exports when present. Require the requested service date, valid service hours, approved nutrition, ingredients, and a positive serving size. Intersect XML recipe IDs with the menu response.
4. Enforce vegetarian/no-egg Monday, Thursday, and Saturday; other days permit chicken as the only meat. Require positive dietary labeling or explicitly chicken ingredients, with prohibited meat/allergen checks.
5. Build 500–625 kcal dining-hall meals from one main protein/entrée and 1–2 sides. The main can be 1, 1.5, or 2 published servings. At least one side must be a vegetable/legume/fruit-type food. Condiment-only and dessert-only meals are excluded.
6. Use the exact requested six-component Monsoon bowl on Tuesday, Wednesday, and Friday lunch when its complete menu and one-swipe policy are verified. The fixed bowl takes precedence over the usual soft calorie band. Weekends use only Café 3 and Crossroads.
7. Ladle & Leaf full salads and grain bowls can be used when their published nutrition fits the band and the official one-swipe policy is still present. The included beverage is declined, so no unverified beverage nutrition is added.
8. Optimize daily calorie/protein fit, discourage repeating food names within the day or from the previous three days' managed tasks, and use a deterministic date-based tie breaker.
9. Re-fetch the selected items' official nutrition popups and match item name, serving size, calories, and protein to the XML. Any disagreement prevents task writes.

Golden Bear Café is fetched but currently excluded from selection: its official page confirms swipe acceptance, but no current official rule for specific eligible combinations was verified. Its foods must not be treated as freely combinable dining-hall items. Add it only after verifying exact combination rules against an official source and implementing tests for those rules.

Snacks are explicitly estimated: 170 kcal / 21 g protein per Kirkland bar, and 300 kcal / 8 g protein per usual trail-mix portion. The optimizer selects 1–2 bars and 0–1.25 usual portions of trail mix in quarter-portion increments. Those are planning assumptions, not verified package labels. Actual package macros and egg-free ingredients must replace those assumptions when available. Daily snack totals appear only in dinner notes, avoiding double counting.

## Duplicate prevention and recovery

- A single GitHub Actions concurrency group serializes runs.
- List all pages, including hidden and completed tasks.
- Match the target date and an anchored `Lunch —`/`Dinner —` prefix (hyphen/en dash also accepted).
- Update existing tasks without resetting their completion status; create only missing tasks.
- Remove only duplicate tasks bearing this application's explicit management marker. Multiple ambiguous legacy tasks stop the run for review rather than deleting unrelated user data.
- Never blindly retry an insertion after a network error. A subsequent run lists tasks again and recovers an insertion that committed before its response was lost.
- Read back both titles, complete notes, due dates, and count after writes.
- Preflight both meal slots before modifying either one.

Google Tasks has no two-task transaction and does not accept an idempotency key for task insertion. An outage can interrupt a run after one update. Rerunning the workflow repairs it. Concurrent writers outside this workflow must remain disabled. This app does not silently invent meals when official data is unavailable, a dining hall is closed, or no compliant combination exists.

## Free deployment setup

The prepared workflow runs once daily at `07:00 America/Los_Angeles`, using GitHub's native timezone field, with an eight-minute job cap, standard Ubuntu runner, no artifact uploads, and no caches. At the cap, 31 daily runs would consume at most 248 runner minutes, before manual/test runs and GitHub's billing rounding. Other repositories share the account allowance.

**Before allocating any hosted runner:** verify remaining included minutes and either that the account has no payment method (usage stops when its free quota is exhausted) or that an effective zero-dollar Actions budget with stop-usage protection prevents paid usage. Never enable a paid allowance. Do not use larger runners. The workflow job is gated by repository variable `ZERO_COST_VERIFIED=true`; leave it unset until this check is completed. The variable is an administrative gate, not an API billing monitor.

The private repository is https://github.com/swapnilbotu/berkeley-meal-planner, with default branch `main`. The October 2026 billing query returned no Actions usage entries. On October 22 the signed-in Budgets page showed an account-wide Actions budget of $0 with Usage blocked. `ZERO_COST_VERIFIED=true` is configured. `GOOGLE_OAUTH_READY=true` is also configured, enabling scheduled runs and manual writes. The setup instructions below are retained for recovery or redeployment; ordinary operation needs no further setup.

## One-time Google authorization

The ChatGPT Google Tasks connector's credentials are not exported. A standalone Google OAuth client and refresh token are required for the independent GitHub runner. Do not paste secrets into chat or commit them.

Using your own Google account:

1. In Google Cloud Console, create or choose a dedicated project **without linking or enabling a billing account**.
2. Enable **Google Tasks API**. If any step requires payment, stop; do not start a paid trial or upgrade.
3. Configure Google Auth Platform branding, audience, and data access for a personal external app. Scopes: `openid`, `email`, `https://www.googleapis.com/auth/tasks`.
4. Configure the consent app as **In production**, not Testing. Testing-mode refresh tokens for Tasks scopes normally expire after seven days. Personal-use/unverified-app restrictions may apply; complete Google's account/security approvals yourself when prompted.
5. Create a **Desktop app** OAuth client and download its client JSON to a trusted local directory outside the repository.
6. On a trusted computer with a browser, Python, and the free GitHub CLI authenticated to the private repository, run:

```bash
python -m pip install -r requirements.txt
python scripts/authorize_google.py --client /path/to/client.json --repo swapnilbotu/berkeley-meal-planner
```

The script uses a local loopback callback, random OAuth state, and PKCE. It verifies the Google email, then sends the client ID, client secret, and refresh token directly to GitHub encrypted Actions secrets via stdin. It does not print tokens, write a token file, or commit credentials. Account consent remains a user-controlled security step.

## Enable and verify

After zero-cost protection and OAuth secrets are verified:

1. Verify `ZERO_COST_VERIFIED=true` remains justified by the account cost controls. After all three Google secrets exist, set `GOOGLE_OAUTH_READY=true` as a repository Actions variable.
2. Confirm `.github/workflows/daily-meals.yml` is on the default branch and the workflow is active.
3. Manually dispatch with `write_tasks=false`; inspect the completed live dry-run log.
4. Dispatch with `write_tasks=true`; require a successful read-back log stating exactly two meal tasks for today's Los Angeles date.
5. Dispatch once more with writes enabled and confirm the same two task IDs remain, including completed/hidden tasks.
6. Confirm the old ChatGPT meal-planning automation is still disabled and no other deployment writes the same tasks.
7. Record the repository URL, commit SHA, workflow URL, run IDs, task IDs, schedule, and cost-control evidence in the deployment report. Only then report production deployment successful.

GitHub can delay or drop scheduled runs under load. A 7:00 AM schedule is not a guarantee of delivery at exactly 7:00:00. Failed workflows expose a red run status and useful logs; notification delivery depends on your GitHub notification settings. No additional reminder/ChatGPT automation is created.

## Official references

- Menu: https://dining.berkeley.edu/menus/
- Menu UI code: https://dining.berkeley.edu/wp-content/plugins/cal-dining/assets/custom.js
- Retail meal equivalencies: https://studentunion.berkeley.edu/food/
- Current meal-plan policy: https://dining.berkeley.edu/meal-plans/2026-2027/living-on-campus/
- GBC: https://dining.berkeley.edu/campus-restaurants/the-golden-bear-cafe/
- GitHub schedules/timezones: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- GitHub free allowance/billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Google Tasks quotas: https://developers.google.com/workspace/tasks/limits
- Google OAuth refresh tokens: https://developers.google.com/identity/protocols/oauth2

The fixture XML and menu HTML contain official public menu data retrieved October 22, 2026. They are test evidence only; production always retrieves fresh data.
