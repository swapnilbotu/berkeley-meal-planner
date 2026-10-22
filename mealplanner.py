"""Deterministic Berkeley menu planner. No inference, paid APIs, or hosted backend."""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from functools import lru_cache
import itertools
import json
import logging
import os
from pathlib import Path
import re
import time
from urllib.parse import quote, urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

LOG = logging.getLogger("mealplanner")
TZ = ZoneInfo("America/Los_Angeles")
MENU = "https://dining.berkeley.edu/menus/"
AJAX = "https://dining.berkeley.edu/wp-admin/admin-ajax.php"
UNION = "https://studentunion.berkeley.edu/food/"
PLAN_POLICY = "https://dining.berkeley.edu/meal-plans/2026-2027/living-on-campus/"
ACCOUNT = "swapnilbotu@gmail.com"
LIST_ID = "MDM4Mzk1Mjg4NzQxODE3ODY0NzU6MDow"
D = Decimal


class VerificationError(RuntimeError):
    pass


def num(value):
    result = D(str(value))
    if not result.is_finite() or result < 0:
        raise VerificationError("Invalid nutrition number")
    return result


def fmt(value):
    return str(D(value).quantize(D(".01"), rounding=ROUND_HALF_UP))


def fetch(url, *, data=None):
    """Only public Berkeley sources. Retrying these POSTs is safe: they are reads."""
    if urlsplit(url).hostname not in {"dining.berkeley.edu", "studentunion.berkeley.edu"}:
        raise VerificationError("Unexpected source host")
    for attempt in range(3):
        try:
            r = requests.request("POST" if data else "GET", url, data=data,
                                 timeout=(10, 30), headers={"User-Agent": "BerkeleyPersonalMealPlanner/1.0"})
            r.raise_for_status()
            if urlsplit(r.url).hostname not in {"dining.berkeley.edu", "studentunion.berkeley.edu"}:
                raise VerificationError("Unexpected redirect host")
            return r.text
        except requests.RequestException:
            if attempt == 2:
                raise VerificationError("Official source unavailable: " + url) from None
            time.sleep(2 ** attempt)


@dataclass(frozen=True)
class Food:
    id: str
    name: str
    category: str
    serving: str
    calories: Decimal
    protein: Decimal
    ingredients: str
    allergens: frozenset[str]
    diets: frozenset[str]
    location: str
    period: str
    day: date
    hours: str
    source: str
    menu_id: str
    location_key: str


@dataclass(frozen=True)
class Meal:
    location: str
    parts: tuple[tuple[Food, Decimal], ...]
    hours: str
    policy: str
    label: str = ""

    @property
    def calories(self):
        return sum((D(fmt(f.calories * n)) for f, n in self.parts), D(0))

    @property
    def protein(self):
        return sum((D(fmt(f.protein * n)) for f, n in self.parts), D(0))

    @property
    def names(self):
        return {f.name for f, _ in self.parts}


def discover_sources(html, day):
    soup = BeautifulSoup(html, "html.parser")
    result = []
    allowed = {"Café 3", "Crossroads", "The Eateries at Student Union", "The Golden Bear Café"}
    for location in soup.select(".location-name"):
        title = location.select_one(".cafe-title")
        if not title or title.get_text(strip=True) not in allowed:
            continue
        first = location.select_one(".recip[data-location]")
        if not first:
            continue
        key = first["data-location"]
        path = base64.b64decode(key, validate=True).decode()
        if not re.fullmatch(r"/code/wp-content/uploads/menus-exportimport/[A-Za-z0-9_]+_" + day.strftime("%Y%m%d") + r"\.xml", path):
            raise VerificationError("Menu source is stale or has an unexpected path")
        ids = {(x["data-menuid"], x["data-id"]) for x in location.select(".recip[data-menuid][data-id]")}
        result.append(("https://dining.berkeley.edu" + path.removeprefix("/code"), key, ids))
    if not result:
        raise VerificationError("No verified menu sources for " + day.isoformat())
    return result


def parse_xml(xml, day, source, location_key, available_ids=None):
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise VerificationError("Unexpected XML declarations")
    root = ET.fromstring(xml)
    foods = []
    for menu in root.findall("menu"):
        if menu.get("servedate") != day.strftime("%Y%m%d"):
            raise VerificationError("Stale menu date")
        period = menu.get("mealperiodname", "")
        if re.search(r"\b(closed|cancelled|canceled|not serving)\b", menu.get("menubulletin", ""), re.I):
            LOG.warning("Skipping service explicitly marked closed")
            continue
        if not any(x in period.lower() for x in ("lunch", "dinner", "brunch")):
            continue
        start, end = menu.get("mealstarttime", ""), menu.get("mealendtime", "")
        if not all(re.fullmatch(r"\d{2}:\d{2}", h) for h in (start, end)) or start >= end:
            LOG.warning("Skipping menu without verified service hours")
            continue
        labels = (menu.findtext("nutrients") or "").strip("|").split("|")
        for recipe in menu.findall("recipes/recipe"):
            rid = recipe.get("id")
            if available_ids is not None and (menu.get("id"), rid) not in available_ids:
                continue
            if recipe.get("approvedNutrition", "").lower() not in {"yes", "y"}:
                continue
            values = recipe.get("nutrients", "").strip("|").split("|")
            if len(values) != len(labels):
                continue
            nutrition = dict(zip(labels, values))
            try:
                calories = num(nutrition["Calories (kcal)"])
                protein = num(nutrition["Protein (g)"])
                serving_size = num(recipe.get("servingSize", ""))
            except (KeyError, ArithmeticError, ValueError, VerificationError):
                continue
            ingredients = (recipe.findtext("ingredients") or "").strip()
            if not ingredients or serving_size <= 0 or not recipe.get("servingSizeUnit"):
                continue
            foods.append(Food(
                rid, recipe.get("shortName", "").strip(), recipe.get("category", ""),
                str(serving_size) + " " + recipe.get("servingSizeUnit"), calories, protein,
                ingredients,
                frozenset(a.get("id", "").lower() for a in recipe.findall("allergens/allergen") if a.text == "Yes"),
                frozenset(a.get("id", "").lower() for a in recipe.findall("dietaryChoices/dietaryChoice") if a.text == "Yes"),
                menu.get("location", ""), period, day, start + "–" + end,
                source, menu.get("id"), location_key))
    return foods


def load_today(day):
    # Date-filtered response is the same request made by the website date control.
    html = fetch(AJAX, data={"action": "cald_filter_xml", "location": "", "mealperiod": "", "date": day.strftime("%Y%m%d")})
    sources = discover_sources(html, day)
    def read(source):
        url, key, ids = source
        return parse_xml(fetch(url), day, url, key, ids)
    with ThreadPoolExecutor(max_workers=4) as pool:
        foods = list(itertools.chain.from_iterable(pool.map(read, sources)))
    LOG.info("Verified %s recipes from %s date-specific XML files", len(foods), len(sources))
    return foods


# Conservative safety filter: positive vegan/vegetarian label, or explicitly chicken.
FORBIDDEN = re.compile(r"\b(beef|pork|bacon|ham|turkey|lamb|mutton|goat|veal|duck|goose|venison|bison|rabbit|quail|fish|salmon|tuna|cod|tilapia|haddock|anchov\w*|bonito|shrimp|prawn\w*|clam\w*|oyster\w*|crab|lobster|mussel\w*|scallop\w*|squid|octopus|gelatin|lard)\b", re.I)
EGG = re.compile(r"\b(eggs?|albumen|mayonnaise)\b", re.I)


def eligible(food, day):
    vegetarian_day = day.weekday() in {0, 3, 5}
    vegan = "vegan option" in food.diets
    vegetarian = vegan or "vegetarian option" in food.diets
    text = food.name + " " + food.ingredients
    if vegetarian_day:
        if not vegetarian or "egg" in food.allergens:
            return False
        # For vegan products, labels establish that terms like plant-based egg are not eggs.
        if not vegan and EGG.search(text):
            return False
    if vegetarian:
        # Permit mock meat names only with official vegan status; still reject flagged allergens.
        return not bool(food.allergens & {"fish", "shellfish", "pork"}) and (vegan or not FORBIDDEN.search(food.ingredients))
    return not vegetarian_day and "chicken" in text.lower() and not FORBIDDEN.search(text) and not bool(food.allergens & {"fish", "shellfish", "pork"})


def policies():
    plan_text = BeautifulSoup(fetch(PLAN_POLICY), "html.parser").get_text(" ", strip=True).lower()
    if "meal swipes" not in plan_text or "dining commons" not in plan_text:
        raise VerificationError("Cannot confirm dining hall swipe policy")
    try:
        union = BeautifulSoup(fetch(UNION), "html.parser").get_text(" ", strip=True).lower()
    except VerificationError:
        LOG.warning("Retail swipe policy unavailable; restricting this run to dining halls")
        union = ""
    return {"hall": PLAN_POLICY,
            "monsoon": UNION if "1 katora bowl + 1 beverage" in union else None,
            "ladle": UNION if "1 salad + 1 beverage" in union and "1 bowl + 1 beverage" in union else None}


def meal_candidates(foods, day, slot, policy):
    relevant = [f for f in foods if f.day == day and eligible(f, day) and
                (slot.lower() in f.period.lower() or slot == "Lunch" and "brunch" in f.period.lower())]
    result = []
    for location in ("Cafe 3", "Crossroads"):
        items = [f for f in relevant if f.location == location]
        # A substantial protein/entrée plus 1–2 non-dessert sides. Seeds, oils and sauces
        # do not become standalone meals, and each portion is at most 2 published servings.
        excluded = re.compile(r"dessert|soft serve|topping|dressing", re.I)
        items = [f for f in items if not excluded.search(f.category + " " + f.name)
                 and not re.search(r"\b(oil|vinegar|seeds?|almond|raisin|crouton|sauce)\b", f.name, re.I)
                 and f.calories >= 15]
        mains = [f for f in items if f.protein >= 8 and f.calories >= 70]
        sides = sorted(items, key=lambda f: (-f.protein / max(f.calories, D(1)), f.name))[:30]
        for main in mains:
            for n in (D(1), D("1.5"), D(2)):
                for k in (1, 2):
                    for extras in itertools.combinations([f for f in sides if f.id != main.id], k):
                        # Require at least one vegetable/legume/fruit side rather than all entrées.
                        if not any(re.search(r"broccoli|carrot|green|spinach|squash|bean|pea|vegetable|zucchini|salad|cucumber|tomato|brussels", f.name, re.I) for f in extras):
                            continue
                        meal = Meal("Café 3" if location == "Cafe 3" else location,
                                    ((main, n),) + tuple((f, D(1)) for f in extras), main.hours, policy["hall"])
                        if 500 <= meal.calories <= 625:
                            result.append(meal)
    if day.weekday() < 5 and slot == "Lunch":
        retail = [f for f in relevant if f.location == "Eateries at the Student Union"]
        if policy.get("ladle"):
            for f in retail:
                if f.category in {"Ladle and Leaf - Salad", "Ladle and Leaf - Grain Bowl"} and not f.name.lower().startswith("half "):
                    if 500 <= f.calories <= 625:
                        result.append(Meal("Ladle & Leaf", ((f, D(1)),), f.hours, policy["ladle"], f.name))
        if day.weekday() in {1, 2, 4} and policy.get("monsoon"):
            required = ("Basmati Rice", "Chicken Tikka Masala", "Aloo Chole", "Samosa", "Tamarind Chutney", "Kachumber Salad")
            by_name = {f.name: f for f in retail if f.category.startswith("Monsoon Katora Bowl")}
            if all(name in by_name for name in required):
                bowl = Meal("Monsoon Kitchens", tuple((by_name[name], D(1)) for name in required),
                            by_name[required[0]].hours, policy["monsoon"], "Chicken katora bowl")
                # Requested fixed bowl takes precedence over the soft per-meal calorie band.
                return [bowl]
            LOG.warning("Monsoon bowl unavailable or not verifiable; using dining hall/eligible retail fallback")
    if not result:
        raise VerificationError("No verified compliant " + slot.lower() + " meal within the calorie band")
    # Preserve options across locations; daily selection considers protein and repeated foods.
    result.sort(key=lambda m: (abs(m.calories-D(585)) + max(D(0),D(32)-m.protein)*8, sorted(m.names)))
    # Keep options from each location so a global cap cannot remove Crossroads.
    counts = {}
    kept = []
    for meal in result:
        if counts.get(meal.location, 0) < 160:
            kept.append(meal)
            counts[meal.location] = counts.get(meal.location, 0) + 1
    return kept


@lru_cache(maxsize=32768)
def snack_plan(calories, protein):
    # User-specific package estimates, never represented as official Berkeley values.
    options = []
    for bars in (1, 2):
        for quarters in range(0, 6):
            mix = D(quarters) / 4
            c, p = D(170)*bars + D(320)*mix, D(21)*bars + D(10)*mix
            score = abs(calories+c-D(1750))/5 + abs(protein+p-D(110))*3
            options.append((score, bars, mix, c, p))
    return min(options)


def choose(foods, day, policy, recent_names=()):
    lunches = meal_candidates(foods, day, "Lunch", policy)
    dinners = meal_candidates(foods, day, "Dinner", policy)
    recent = set(recent_names)
    def macro_score(pair):
        c = sum(meal.calories for meal in pair)
        p = sum(meal.protein for meal in pair)
        return snack_plan(c, p)[0] + max(D(0), D(60)-p)*2

    # Prefer fewer Café 3 visits among plans with a similar daily macro fit.
    # A 20-point tolerance is 100 kcal OR about 6.7 g protein of target error
    # under the existing scoring weights; combined errors also count.
    # Retail eligibility and the fixed Monsoon lunch are already enforced above.
    best_macro = min(macro_score(pair) for pair in itertools.product(lunches, dinners))
    def score(pair):
        lunch, dinner = pair
        repeated = len(lunch.names & dinner.names)*15 + len((lunch.names | dinner.names) & recent)*5
        tie = hashlib.sha256((day.isoformat()+"|"+"|".join(sorted(lunch.names))+"/"+"|".join(sorted(dinner.names))).encode()).hexdigest()
        return (sum(meal.location == "Café 3" for meal in pair), macro_score(pair)+repeated, tie)
    close_plans = (pair for pair in itertools.product(lunches, dinners)
                   if macro_score(pair) <= best_macro+D(20))
    return min(close_plans, key=score)


def verify_panels(meals):
    """Cross-check selected XML values against the actual popup endpoint before writes."""
    unique = {(f.location_key, f.menu_id, f.id): f for m in meals for f, _ in m.parts}
    def check(f):
        s = BeautifulSoup(fetch(AJAX, data={"action":"get_recipe_details", "location":f.location_key,
                                           "id":f.id, "menu_id":f.menu_id}), "html.parser")
        rows = {}
        for li in s.select(".nutration-details li"):
            label = li.find("span")
            if label:
                text = label.get_text(strip=True).rstrip(":")
                label.extract()
                rows[text] = li.get_text(strip=True)
        serving = s.select_one(".serving-size")
        heading = s.select_one("h5")
        if not serving or not heading or heading.get_text(strip=True) != f.name:
            raise VerificationError("Nutrition popup identity mismatch: " + f.name)
        if " ".join(serving.get_text().split()).removeprefix("Serving Size: ") != f.serving:
            raise VerificationError("Serving size mismatch: " + f.name)
        if num(rows.get("Calories (kcal)", "NaN")) != f.calories or num(rows.get("Protein (g)", "NaN")) != f.protein:
            raise VerificationError("Nutrition popup differs from XML: " + f.name)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(check, unique.values()))
    LOG.info("Cross-checked %s selected nutrition panels", len(unique))


def task_payloads(day, meals):
    c, p = sum(m.calories for m in meals), sum(m.protein for m in meals)
    _, bars, mix, sc, sp = snack_plan(c, p)
    result = []
    for slot, meal in zip(("Lunch", "Dinner"), meals):
        lines = [f"Where: {meal.location}",
                 f"Meal: {meal.label or ' + '.join(f.name for f, _ in meal.parts)}"]
        for f, n in meal.parts:
            station = f" [{f.category.strip()}]" if meal.location in {"Café 3", "Crossroads"} and f.category.strip() else ""
            lines.append(f"- {f.name}{station} — {n} published serving(s); ({fmt(f.calories*n)} C, {fmt(f.protein*n)} P)")
        lines.append(f"Total: {fmt(meal.calories)} C, {fmt(meal.protein)} P")
        if meal.location in {"Monsoon Kitchens", "Ladle & Leaf"}:
            lines.append("Decline the included beverage.")
        if slot == "Dinner":
            # The flavor is not fixed: show the user-supplied protein range.
            protein_range = f"{fmt(sp)}–{fmt(sp+bars)}"
            lines += ["", "Daily snack plan (estimates):",
                      f"- Kirkland protein bar, Chocolate Peanut Butter Chip or Cookies & Cream: {bars} bar(s) ({170*bars} C, {21*bars}–{22*bars} P).",
                      f"- Kirkland trail mix with M&Ms: {mix} × your usual portion ({fmt(320*mix)} C, {fmt(10*mix)} P).",
                      "",
                      f"Meals: {fmt(c)} C, {fmt(p)} P; snack estimates: {fmt(sc)} C, {protein_range} P.",
                      f"Estimated day total: {fmt(c+sc)} C, {fmt(p+sp)}–{fmt(p+sp+bars)} P."]
        result.append({"title":f"{slot} — {meal.location} / {meal.label or meal.parts[0][0].name}",
                       "notes":"\n".join(lines), "due":day.isoformat()+"T00:00:00Z"})
    return result


class Tasks:
    def __init__(self):
        self.session = requests.Session()
        secrets = [os.environ.get(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")]
        if not all(secrets):
            raise VerificationError("Missing Google OAuth secrets")
        r = self.session.post("https://oauth2.googleapis.com/token", data=dict(zip(
            ("client_id", "client_secret", "refresh_token"), secrets)) | {"grant_type":"refresh_token"}, timeout=30)
        if not r.ok:
            raise VerificationError("Google OAuth refresh failed; reauthorize the account (no tokens logged)")
        token = r.json().get("access_token")
        if not token:
            raise VerificationError("Google OAuth did not return access token")
        self.session.headers["Authorization"] = "Bearer " + token
        # Bootstrap requests openid/email in addition to Tasks; verify the account each run.
        user = self.session.get("https://openidconnect.googleapis.com/v1/userinfo", timeout=30)
        if not user.ok or user.json().get("email", "").lower() != ACCOUNT or not user.json().get("email_verified"):
            raise VerificationError("OAuth account is not the expected verified email")
        lists = self.pages("users/@me/lists", {})
        matching = [x for x in lists if x.get("id") == LIST_ID and x.get("title") == "My Tasks"]
        if len(matching) != 1:
            raise VerificationError("Expected existing My Tasks list not found; refusing to create a list")

    def call(self, method, path, *, params=None, body=None):
        # Never blindly retry task insertion: a lost response may already have committed.
        for attempt in range(3 if method in {"GET", "PATCH", "DELETE"} else 1):
            try:
                r = self.session.request(method, "https://tasks.googleapis.com/tasks/v1/"+path,
                                         params=params, json=body, timeout=30)
                if r.status_code in {429, 500, 502, 503, 504} and attempt < 2 and method != "POST":
                    time.sleep(2**attempt)
                    continue
                if not r.ok:
                    raise VerificationError(f"Google Tasks {method} failed (HTTP {r.status_code})")
                return r.json() if r.content else {}
            except requests.RequestException:
                if method == "POST" or attempt == 2:
                    raise VerificationError("Google Tasks request interrupted; rerun will reconcile existing tasks") from None
                time.sleep(2**attempt)
        raise VerificationError("Google Tasks retries exhausted")

    def pages(self, path, params):
        items, token = [], None
        while True:
            page = self.call("GET", path, params=params | {"maxResults":100} | ({"pageToken":token} if token else {}))
            items += page.get("items", [])
            token = page.get("nextPageToken")
            if not token:
                return items

    def tasks(self, start, end):
        return self.pages(f"lists/{quote(LIST_ID)}/tasks", {"dueMin":start.isoformat()+"T00:00:00Z",
            "dueMax":end.isoformat()+"T00:00:00Z", "showCompleted":"true", "showHidden":"true", "showDeleted":"false"})


def matching_tasks(tasks, day, slot):
    # Exact meal prefix and due date. Unrelated tasks and other dates are never touched.
    pattern = re.compile(r"^"+slot+r"\s*(?:—|–|-)\s*", re.I)
    return [t for t in tasks if not t.get("deleted") and t.get("due", "")[:10] == day.isoformat()
            and pattern.match(t.get("title", ""))]


def reconcile(client, day, payloads):
    if len(payloads) != 2 or any(p.get("due", "")[:10] != day.isoformat() for p in payloads):
        raise VerificationError("Expected exactly two task payloads for this date")
    existing = client.tasks(day, day+timedelta(days=1))
    # Preflight both slots before changing either one.
    for slot in ("Lunch", "Dinner"):
        unmanaged = [t for t in matching_tasks(existing, day, slot)
                     if f"[berkeley-meal-planner:{day.isoformat()}:" not in t.get("notes", "")]
        if len(unmanaged) > 1:
            raise VerificationError("Multiple legacy meal tasks need review; no duplicate created")
    path = f"lists/{quote(LIST_ID)}/tasks"
    for slot, payload in zip(("Lunch", "Dinner"), payloads):
        matches = matching_tasks(existing, day, slot)
        if len(matches) > 1:
            # Only remove duplicates created by this app. Ambiguous legacy tasks require review.
            unmanaged = [t for t in matches if f"[berkeley-meal-planner:{day.isoformat()}:" not in t.get("notes", "")]
            if len(unmanaged) > 1:
                raise VerificationError("Multiple legacy meal tasks need review; no duplicate created")
            keep = unmanaged[0] if unmanaged else sorted(matches, key=lambda t:t["id"])[0]
            for duplicate in matches:
                if duplicate["id"] != keep["id"]:
                    client.call("DELETE", path+"/"+quote(duplicate["id"]))
            matches = [keep]
        if matches:
            client.call("PATCH", path+"/"+quote(matches[0]["id"]), body=payload)
            LOG.info("Updated existing %s task; completion status preserved", slot)
        else:
            client.call("POST", path, body=payload)
            LOG.info("Created missing %s task", slot)
    checked = client.tasks(day, day+timedelta(days=1))
    for slot, expected in zip(("Lunch", "Dinner"), payloads):
        found = matching_tasks(checked, day, slot)
        if len(found) != 1 or any(found[0].get(k) != v for k,v in expected.items() if k != "due"):
            raise VerificationError("Task read-back verification failed: " + slot)
    LOG.info("Read-back verified exactly two meal tasks due %s", day)


def recent_food_names(tasks, day):
    names = []
    for task in tasks:
        if task.get("deleted") or task.get("due", "")[:10] >= day.isoformat():
            continue
        if not re.match(r"^(Lunch|Dinner)\s*(?:—|–|-)\s*", task.get("title", ""), re.I):
            continue
        notes = task.get("notes", "")
        if "Where: " not in notes or "Meal: " not in notes:
            continue
        # Supports old verbose notes and compact station labels without a visible ID marker.
        for name in re.findall(r"^- (.+?) — ", notes, re.M):
            names.append(re.sub(r" \[[^\]\n]*\]$", "", name))
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--write", action="store_true", help="Write and verify Google Tasks; default is read-only dry run")
    parser.add_argument("--output", default="out/plan.json")
    args = parser.parse_args()
    day = args.date or datetime.now(TZ).date()
    if args.write and day != datetime.now(TZ).date():
        raise VerificationError("Writes are limited to today's Los Angeles date")
    client = Tasks() if args.write else None
    recent = recent_food_names(client.tasks(day-timedelta(days=3), day), day) if client else []
    meals = choose(load_today(day), day, policies(), recent)
    LOG.info("Golden Bear Café excluded: exact eligible swipe combinations not independently verified")
    verify_panels(meals)
    payloads = task_payloads(day, meals)
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payloads, indent=2, ensure_ascii=False)+"\n")
    for slot, meal in zip(("Lunch", "Dinner"), meals):
        LOG.info("%s: %s, %s kcal, %s g protein, 1 swipe", slot, meal.location, meal.calories, meal.protein)
    if client:
        reconcile(client, day, payloads)
    else:
        LOG.info("Dry run complete; no Google Tasks changes")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        main()
    except (VerificationError, ET.ParseError) as exc:
        LOG.error("Run stopped: %s", exc)
        raise SystemExit(1)
