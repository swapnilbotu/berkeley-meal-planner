# Berkeley Meal Planner

Turn UC Berkeley dining menus into **two meals you can order with your meal swipes**. I built this to spend less time checking menus and adding up nutrition facts. Every morning, the planner selects lunch and dinner and puts both in Google Tasks.

- **One swipe per meal.** The planner checks dining hall and eligible retail options against meal-swipe rules.
- **A plan you can follow in line.** Each task lists where to go, what to order, where to find each item when station data is available, and how much to get.
- **Nutrition you can trace.** Calories, protein, and serving sizes are checked against Berkeley’s published data. Snack estimates are labeled separately.

Built with Python, Requests, Beautiful Soup, GitHub Actions, cron-job.org, and the Google Tasks API. The planner uses rule-based scoring and runs without paid hosting or AI inference.

## What a task looks like

A sample lunch task from Monsoon Kitchens, abridged:

```text
Lunch — Monsoon Kitchens / Chicken katora bowl

- Basmati Rice — 1 published serving (181.55 C, 3.63 P)
- Chicken Tikka Masala — 1 published serving (179.51 C, 21.90 P)
- Aloo Chole — 1 published serving (85.09 C, 3.65 P)
- Samosa — 1 published serving (95.37 C, 1.44 P)
- Tamarind Chutney — 1 published serving (35.46 C, 0.00 P)
- Kachumber Salad — 1 published serving (4.37 C, 0.18 P)

Total: 581.35 calories · 30.80 g protein
```

Dinner also includes an estimated daily total with snacks. This example illustrates the output; availability changes with the menu.

## How it works

1. **Find today’s menu.** Read Berkeley Dining’s date-filtered menu and match its listed dishes to the corresponding XML exports.
2. **Build and rank meals.** Apply dietary rules and food exclusions, then compare portions, calories, protein, and variety. The planner prefers Crossroads when the nutrition fit is comparable and can select a verified Monsoon Kitchens bowl on eligible days.
3. **Verify the selection.** Cross-check each selected item’s name, serving size, calories, and protein against its official nutrition panel. If a plan can’t be verified, stop before writing tasks.
4. **Sync Google Tasks.** Match lunch and dinner by due date and title. Update existing tasks without clearing completion status, create missing tasks, and read both back. Recovery runs preserve a complete plan.

The daily trigger runs at **7:00 a.m. Pacific**, with a **7:15 a.m. recovery check** and a later GitHub Actions fallback. A trigger starts the workflow; task delivery depends on the menu and Google Tasks APIs being available.

## Try it locally

Requires Python 3.12+. Run from the repository root, preferably in a virtual environment:

```bash
python -m pip install -r requirements.txt
python mealplanner.py
```

This is a **live dry run**: it fetches public Berkeley menus and writes a local preview to `out/plan.json`. It needs no Google credentials and makes no Google Tasks changes. Use `--date YYYY-MM-DD` for another date with published menu data.

To run the regression tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover menu validation, dietary exclusions, nutrition checks, and recovery without duplicate tasks.

## Automation setup

The live deployment is personal. To run your own copy, use your own Google OAuth configuration and an existing `My Tasks` list. Configure these as environment variables for local writes or as GitHub Actions secrets for hosted runs:

| Setting | Purpose |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | Google Tasks authorization |
| `MEAL_TASKS_ACCOUNT` | Expected verified Google email |
| `MEAL_TASKS_LIST_ID` | ID of the existing destination list |

The [OAuth bootstrap script](scripts/authorize_google.py) accepts `--client /path/to/client.json` and `--repo OWNER/REPO`. Set `MEAL_TASKS_ACCOUNT` first and keep the OAuth client file outside the repo. Once configured, `python mealplanner.py --write` writes only for today in Pacific time. Add `--if-missing` to preserve a complete plan.

For hosted runs, verify zero-cost usage before setting `ZERO_COST_VERIFIED=true`. Set `GOOGLE_OAUTH_READY=true` only after configuring the destination and credentials. See the [scheduler setup](docs/external-scheduler.md) for dispatch and recovery details.

Menu and policy sources: [Berkeley Dining](https://dining.berkeley.edu/menus/) · [Student Union dining](https://studentunion.berkeley.edu/food/).
