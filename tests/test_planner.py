from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import copy
import json
import gzip

import pytest

import mealplanner as m

DAY = date(2026, 10, 22)
FIXTURES = Path(__file__).parent/'fixtures'
POLICY = {'hall':m.PLAN_POLICY, 'monsoon':m.UNION, 'ladle':m.UNION}

def fixture(name):
    return gzip.decompress((FIXTURES/(name+'.gz')).read_bytes()).decode('utf-8')


@pytest.fixture(scope='module')
def foods():
    sources = m.discover_sources(fixture('menu-20261022.html'), DAY)
    return [f for url,key,ids in sources for f in m.parse_xml(fixture(url.rsplit('/',1)[-1]), DAY, url,key,ids)]


@pytest.fixture(scope='module')
def meals(foods):
    return m.choose(foods, DAY, POLICY)


def test_official_known_values(foods):
    f = next(f for f in foods if f.name == 'Baked Tofu Piccata')
    assert (f.serving, f.calories, f.protein) == ('4.52 oz', m.D('208.59'), m.D('18.12'))


def test_stale_source_rejected():
    with pytest.raises(m.VerificationError, match='stale'):
        m.discover_sources(fixture('menu-20261022.html'), DAY+timedelta(days=1))


def test_stale_xml_rejected():
    with pytest.raises(m.VerificationError, match='Stale'):
        m.parse_xml(fixture('Cafe_3_20261022.xml'), DAY+timedelta(days=1),'source','key')


def test_absent_menu_fails_closed():
    with pytest.raises(m.VerificationError):
        m.discover_sources('<div>No menu</div>', DAY)


def test_missing_nutrients_never_become_zero():
    xml = fixture('Cafe_3_20261022.xml').replace('Protein (g)', 'missing')
    assert m.parse_xml(xml, DAY, 'source', 'key') == []


def test_date_xml_entity_block():
    with pytest.raises(m.VerificationError):
        m.parse_xml('<!DOCTYPE test><x/>',DAY,'','')


@pytest.mark.parametrize('value', ['NaN','Infinity','-1'])
def test_invalid_nutrition(value):
    with pytest.raises(m.VerificationError):
        m.num(value)


def test_exactly_two_balanced_vegetarian_meals(meals):
    assert len(meals) == 2
    for meal in meals:
        assert 500 <= meal.calories <= 625
        assert all(m.eligible(f, DAY) and 'egg' not in f.allergens for f,n in meal.parts)
    assert not meals[0].names & meals[1].names
    c,p = sum(x.calories for x in meals),sum(x.protein for x in meals)
    _,_,_,sc,sp = m.snack_plan(c,p)
    assert abs(c+sc-1750) <= 100
    assert p+sp >= 100


@pytest.mark.parametrize('day', [date(2026,10,24), date(2026,10,25)])
def test_weekends_halls_only(foods,day):
    candidates = m.meal_candidates([replace(f,day=day) for f in foods],day,'Lunch',POLICY)
    assert {x.location for x in candidates} <= {'Café 3','Crossroads'}


@pytest.mark.parametrize('day', [date(2026,10,20),date(2026,10,21),date(2026,10,23)])
def test_monsoon_exact_components(foods,day):
    candidates = m.meal_candidates([replace(f,day=day) for f in foods],day,'Lunch',POLICY)
    assert len(candidates) == 1 and candidates[0].location == 'Monsoon Kitchens'
    assert candidates[0].names == {'Basmati Rice','Chicken Tikka Masala','Aloo Chole','Samosa','Tamarind Chutney','Kachumber Salad'}
    assert candidates[0].calories == m.D('581.35')
    assert candidates[0].protein == m.D('30.80')


def test_monsoon_missing_component_falls_back(foods):
    day = date(2026,10,23)
    selected = m.meal_candidates([replace(f,day=day) for f in foods if f.name != 'Samosa'],day,'Lunch',POLICY)
    assert all(x.location != 'Monsoon Kitchens' for x in selected)


def test_retail_policy_missing_falls_back(foods):
    day = date(2026,10,23)
    result = m.meal_candidates([replace(f,day=day) for f in foods],day,'Lunch',{'hall':m.PLAN_POLICY})
    assert all(x.location in {'Café 3','Crossroads'} for x in result)


def test_eggs_and_broth_rejected(foods):
    f = foods[0]
    assert not m.eligible(replace(f,name='Chicken bowl',diets=frozenset(),ingredients='Chicken, beef broth',allergens=frozenset()),date(2026,10,23))
    assert not m.eligible(replace(f,diets=frozenset({'vegetarian option'}),allergens=frozenset({'egg'})),DAY)
    assert not m.eligible(replace(f,name='Turkey',diets=frozenset(),ingredients='Turkey',allergens=frozenset()),date(2026,10,23))


@pytest.mark.parametrize('name', ['Edamame Potsticker', 'Vegetable Potstickers', 'POT STICKERS', 'Chicken pot-stickers'])
@pytest.mark.parametrize('day', [DAY, date(2026,10,23)])
def test_potstickers_excluded_regardless_of_dietary_label(foods, name, day):
    vegan = replace(foods[0], name=name, diets=frozenset({'vegan option'}),
                    ingredients='Vegetables, flour', allergens=frozenset())
    assert not m.eligible(vegan, day)
    chicken = replace(vegan, diets=frozenset(), ingredients='Chicken, flour')
    assert not m.eligible(chicken, day)
    assert m.eligible(replace(vegan, name='Baked Lemongrass Tofu'), day)


@pytest.mark.parametrize('name', ['Vegan Italian "Sausage"', 'Chicken Sausages', 'Soyrizo', 'Plant-based Bratwurst'])
@pytest.mark.parametrize('field', ['name', 'ingredients'])
@pytest.mark.parametrize('day', [DAY, date(2026,10,23)])
def test_sausages_excluded_in_names_and_ingredients(foods, name, field, day):
    food = replace(foods[0], name='Vegetable bowl', ingredients='Tofu, rice',
                   diets=frozenset({'vegan option'}), allergens=frozenset())
    assert m.eligible(food, day)
    assert not m.eligible(replace(food, **{field: name}), day)


def test_payload_reconciles_and_date_only(meals):
    payload = m.task_payloads(DAY, meals)
    assert len(payload)==2
    assert all(t['due']=='2026-10-22T00:00:00Z' for t in payload)
    assert all(t['notes'].startswith('Where: ') for t in payload)
    assert all('[berkeley-meal-planner:' not in t['notes'] for t in payload)
    assert 'Daily snack plan' not in payload[0]['notes']
    assert 'Daily snack plan (estimates):' in payload[1]['notes']
    assert all(len(t['notes']) < 8192 for t in payload)


class FakeTasks:
    def __init__(self, tasks=None):
        self.items=copy.deepcopy(tasks or [])
        self.calls=[]
        self.lose_insert_response=False

    def tasks(self,start,end):
        return copy.deepcopy(self.items)

    def call(self,method,path,body=None):
        self.calls.append(method)
        if method=='POST':
            self.items.append(body|{'id':str(len(self.items)+1),'status':'needsAction'})
            if self.lose_insert_response:
                self.lose_insert_response=False
                raise m.VerificationError('lost response')
        elif method=='PATCH':
            next(t for t in self.items if t['id']==path.rsplit('/',1)[-1]).update(body)
        elif method=='DELETE':
            self.items=[t for t in self.items if t['id']!=path.rsplit('/',1)[-1]]
        return {}


def test_idempotent_rerun_and_completed_hidden(meals):
    payload=m.task_payloads(DAY,meals)
    client=FakeTasks([{'id':'legacy','title':'Lunch — previous meal','due':payload[0]['due'],
                       'status':'completed','hidden':True},
                      {'id':'unrelated','title':'Study','due':payload[0]['due']}])
    m.reconcile(client,DAY,payload)
    m.reconcile(client,DAY,payload)
    assert len(client.items)==3 and client.calls.count('POST')==1
    assert client.items[0]['status']=='completed' and client.items[0]['hidden']
    assert client.items[1]['title']=='Study'


@pytest.mark.parametrize('present', [0, 1, 2])
def test_recovery_creates_missing_plan_without_changing_complete_plan(monkeypatch, tmp_path, meals, present):
    day = datetime.now(m.TZ).date()
    payloads = m.task_payloads(day, meals)
    existing = [p | {'id':str(i), 'status':'completed', 'hidden':True}
                for i, p in enumerate(payloads[:present])]
    client = FakeTasks(existing)
    monkeypatch.setattr(m, 'Tasks', lambda:client)
    source_calls = []
    monkeypatch.setattr(m, 'load_today', lambda day:source_calls.append(day))
    monkeypatch.setattr(m, 'policies', lambda:POLICY)
    monkeypatch.setattr(m, 'choose', lambda *args:meals)
    monkeypatch.setattr(m, 'verify_panels', lambda meals:None)
    output = tmp_path/'plan.json'
    m.main(['--write', '--if-missing', '--output', str(output)])
    assert len(client.items) == 2
    assert client.calls.count('POST') == 2-present
    assert bool(source_calls) == (present < 2)
    if present == 2:
        assert client.calls == [] and client.items == existing
    assert json.loads(output.read_text()) == payloads
    before = copy.deepcopy(client.items)
    client.calls.clear()
    m.main(['--write', '--if-missing', '--output', str(output)])
    assert client.calls == [] and client.items == before


def test_recovery_rejects_duplicates_and_does_not_accept_other_dates(meals):
    payloads = m.task_payloads(DAY, meals)
    assert m.existing_plan(FakeTasks(payloads), DAY+timedelta(days=1)) is None
    assert m.existing_plan(FakeTasks([payloads[0], payloads[1] | {'notes':''}]), DAY) is None
    with pytest.raises(m.VerificationError):
        m.existing_plan(FakeTasks(payloads+[payloads[0]]), DAY)


@pytest.mark.parametrize('utc,should_run', [
    ('2026-10-24T13:59:00+00:00', False),
    ('2026-10-24T14:00:00+00:00', True),
    ('2026-11-01T14:23:00+00:00', False),
    ('2026-11-01T15:00:00+00:00', True),
    ('2027-03-14T14:00:00+00:00', True),
])
def test_utc_schedule_guard_across_dst(monkeypatch, tmp_path, meals, utc, should_run):
    instant = datetime.fromisoformat(utc)
    class Clock:
        @staticmethod
        def now(tz):
            return instant.astimezone(tz)
    monkeypatch.setattr(m, 'datetime', Clock)
    day = instant.astimezone(m.TZ).date()
    client = FakeTasks(m.task_payloads(day, meals))
    auth_calls = []
    def auth():
        auth_calls.append(True)
        return client
    monkeypatch.setattr(m, 'Tasks', auth)
    m.main(['--write','--if-missing','--scheduled','--output',str(tmp_path/'plan.json')])
    assert bool(auth_calls) == should_run
    assert client.calls == []


def test_lost_insert_response_does_not_duplicate_on_rerun(meals):
    payload=m.task_payloads(DAY,meals)
    client=FakeTasks();client.lose_insert_response=True
    with pytest.raises(m.VerificationError):m.reconcile(client,DAY,payload)
    m.reconcile(client,DAY,payload)
    assert len(client.items)==2


def test_duplicate_managed_tasks_reconciled(meals):
    payload=m.task_payloads(DAY,meals)
    marked=payload[0]|{'notes':payload[0]['notes']+f'\n[berkeley-meal-planner:{DAY}:lunch]'}
    client=FakeTasks([marked|{'id':'1'},marked|{'id':'2'}])
    m.reconcile(client,DAY,payload)
    assert len(client.items)==2 and 'DELETE' in client.calls


def test_ambiguous_legacy_duplicates_stop(meals):
    payload=m.task_payloads(DAY,meals)
    a=payload[0]|{'notes':'legacy'}
    client=FakeTasks([a|{'id':'1'},a|{'id':'2'}])
    with pytest.raises(m.VerificationError,match='legacy'):m.reconcile(client,DAY,payload)
    assert client.calls==[]


def test_other_dates_untouched(meals):
    payload=m.task_payloads(DAY,meals)
    old=payload[0]|{'id':'old','due':'2026-10-21T00:00:00Z'}
    client=FakeTasks([old]);m.reconcile(client,DAY,payload)
    assert client.items[0]==old and len(client.items)==3


def test_google_pagination():
    client=object.__new__(m.Tasks)
    calls=[]
    def call(method,path,params):
        calls.append(params)
        return {'items':[{'id':'2'}]} if 'pageToken' in params else {'items':[{'id':'1'}],'nextPageToken':'next'}
    client.call=call
    assert [t['id'] for t in client.pages('tasks',{})]==['1','2']
    assert calls[1]['pageToken']=='next'


@pytest.mark.parametrize('utc,local_day,hour',[
    ('2026-07-01T14:00:00+00:00',date(2026,7,1),7),
    ('2026-12-01T15:00:00+00:00',date(2026,12,1),7),
    ('2026-10-23T01:00:00+00:00',date(2026,10,22),18),
])
def test_local_date_and_dst(utc,local_day,hour):
    local=datetime.fromisoformat(utc).astimezone(m.TZ)
    assert local.date()==local_day and local.hour==hour


def test_missing_oauth_secrets_fails(monkeypatch):
    for key in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REFRESH_TOKEN'):
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(m.VerificationError,match='Missing Google'):m.Tasks()


def test_explicit_closure_not_used():
    xml=fixture('Cafe_3_20261022.xml').replace('menubulletin=""','menubulletin="Closed today"')
    assert m.parse_xml(xml,DAY,'source','key')==[]


def test_stale_food_candidates_not_used(foods):
    with pytest.raises(m.VerificationError):
        m.meal_candidates(foods,DAY+timedelta(days=1),'Lunch',POLICY)


def test_popup_mismatch_blocks_write(monkeypatch,meals):
    monkeypatch.setattr(m,'fetch',lambda *a,**k:'<h5>Wrong food</h5>')
    with pytest.raises(m.VerificationError,match='identity mismatch'):
        m.verify_panels(meals)


def test_second_slot_legacy_conflict_preflight(meals):
    payload=m.task_payloads(DAY,meals)
    dinner=payload[1]|{'notes':'legacy'}
    client=FakeTasks([dinner|{'id':'1'},dinner|{'id':'2'}])
    with pytest.raises(m.VerificationError,match='legacy'):m.reconcile(client,DAY,payload)
    assert client.calls==[]


def test_malformed_payload_stops_before_write(meals):
    client=FakeTasks()
    with pytest.raises(m.VerificationError):m.reconcile(client,DAY,m.task_payloads(DAY,meals)[:1])
    assert client.calls==[]


def test_readback_disagreement_fails(meals):
    client=FakeTasks()
    original=client.tasks
    def bad_read(start,end):
        found=original(start,end)
        for t in found:t['notes']='Unexpected external modification'
        return found
    client.tasks=bad_read
    with pytest.raises(m.VerificationError,match='read-back'):
        m.reconcile(client,DAY,m.task_payloads(DAY,meals))


def test_optional_retail_policy_outage(monkeypatch):
    def fetch(url):
        if url==m.UNION:raise m.VerificationError('unavailable')
        return '<p>Meal swipes at dining commons</p>'
    monkeypatch.setattr(m,'fetch',fetch)
    assert m.policies()=={'hall':m.PLAN_POLICY,'monsoon':None,'ladle':None}


def test_compact_stations_and_snack_range(foods):
    def food(name, period):
        return next(f for f in foods if f.name == name and period in f.period and f.location == 'Crossroads')
    lunch=m.Meal('Crossroads',((food('Paprika Rosemary Tofu','Lunch'),m.D(2)),(food('Bean Chili','Lunch'),m.D(1)),(food('Hummus','Lunch'),m.D(1))),'','')
    dinner=m.Meal('Crossroads',((food('Baked Tofu Piccata','Dinner'),m.D('1.5')),(food('Sweet & Sour Tofu','Dinner'),m.D(1)),(food('Green Beans Garlic Stir Fry','Dinner'),m.D(1))),'','')
    notes=m.task_payloads(DAY,(lunch,dinner))[1]['notes']
    assert 'Baked Tofu Piccata [Centerplate] — 1.5 published serving(s); (312.89 C, 27.18 P)' in notes
    assert 'Sweet & Sour Tofu [Lemongrass]' in notes
    assert 'Total: 598.77 C, 46.07 P' in notes
    assert '1 bar(s) (170 C, 21–22 P)' in notes
    assert '1 × your usual portion (320.00 C, 10.00 P)' in notes
    assert 'snack estimates: 490.00 C, 31.00–32.00 P' in notes
    assert 'Estimated day total: 1691.43 C, 110.01–111.01 P' in notes
    assert 'XML source' not in notes and 'Service hours' not in notes


def test_history_handles_compact_notes_without_marker(meals):
    tasks=m.task_payloads(DAY,meals)
    names=m.recent_food_names(tasks, DAY+timedelta(days=1))
    assert set(names)==set.union(*(meal.names for meal in meals))
    assert m.recent_food_names(tasks,DAY)==[]
    assert m.recent_food_names([tasks[0]|{'title':'Study'}],DAY+timedelta(days=1))==[]


@pytest.mark.parametrize('cross_protein,expected', [('39','Crossroads'),('10','Café 3')])
def test_crossroads_preferred_unless_macros_materially_worse(monkeypatch,foods,cross_protein,expected):
    def meal(location,name,protein):
        f=replace(foods[0],name=name,calories=m.D(600),protein=m.D(protein))
        return m.Meal(location,((f,m.D(1)),),'','')
    lunch_cross=meal('Crossroads','Crossroads lunch',cross_protein)
    lunch_cafe=meal('Café 3','Cafe lunch','39')
    dinner=meal('Crossroads','Dinner','40')
    monkeypatch.setattr(m,'meal_candidates',lambda foods,day,slot,policy: [lunch_cross,lunch_cafe] if slot=='Lunch' else [dinner])
    # Recent repetition cannot override the hall preference when macros match.
    selected=m.choose([],DAY,POLICY,recent_names=['Crossroads lunch'])
    assert selected[0].location==expected


def test_crossroads_preference_does_not_override_monsoon(foods):
    day=date(2026,10,23)
    selected=m.choose([replace(f,day=day) for f in foods],day,POLICY)
    assert selected[0].location=='Monsoon Kitchens'
