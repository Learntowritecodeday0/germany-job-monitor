#!/usr/bin/env python3
"""Conservative worksite display. Only map cities actually named in the job location.

Never substitute employer headquarters for the worksite. Country hints from the
public feed are labelled as such. No external geocoding or applicant data is used.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'data/state.json'
PUBLIC = ROOT / 'docs/jobs.json'

# German municipalities and known state names, matched with word boundaries.
# Only explicit city mentions are used; regional/office names are not guessed.
GERMAN_STATES = {
 'Bayern': 'Munich|München|Garching|Planegg|Martinsried|Neuried|Gräfelfing|Haar|Oberschleißheim|Unterschleißheim|Puchheim|Germering|Freising|Maisach|Karlsfeld|Taufkirchen|Oberpfaffenhofen|Weßling|Wessling|Starnberg|Fürstenfeldbruck|Gauting|Penzberg|Geretsried|Würzburg|Erlangen|Nürnberg|Nuremberg|Regensburg|Augsburg|Burghausen|Wasserburg am Inn|Wasserburg|Ingolstadt|Alzenau|Bayreuth|Coburg|Aschaffenburg|Schweinfurt|Kaufbeuren|Memmingen|Eresing|Emmering|Inning am Ammersee|Landsberg',
 'Baden-Württemberg': 'Stuttgart|Ulm|Karlsruhe|Heidelberg|Freiburg|Tübingen|Esslingen|Heilbronn|Pforzheim|Konstanz|Oberkochen|Mannheim|Reutlingen|Friedrichshafen|Ravensburg|Singen',
 'Hessen': 'Frankfurt am Main|Frankfurt|Darmstadt|Hanau|Kronberg|Wiesbaden|Fulda|Marburg|Kassel|Gießen|Giessen|Rüsselsheim',
 'Nordrhein-Westfalen': 'Aachen|Köln|Cologne|Düsseldorf|Essen|Bonn|Leverkusen|Schwelm|Dortmund|Duisburg|Münster|Bielefeld|Paderborn|Bochum|Krefeld',
 'Sachsen': 'Dresden|Leipzig|Zwickau|Freiberg|Chemnitz|Plauen|Görlitz',
 'Sachsen-Anhalt': 'Halle|Magdeburg|Möckern|Dessau',
 'Niedersachsen': 'Hannover|Braunschweig|Osnabrück|Göttingen|Wolfsburg|Oldenburg|Hildesheim',
 'Berlin': 'Berlin',
 'Hamburg': 'Hamburg',
 'Bremen': 'Bremen|Bremerhaven',
 'Rheinland-Pfalz': 'Mainz|Koblenz|Kaiserslautern|Ludwigshafen|Trier',
 'Schleswig-Holstein': 'Kiel|Lübeck|Flensburg',
 'Mecklenburg-Vorpommern': 'Rostock|Schwerin|Greifswald',
 'Brandenburg': 'Potsdam|Cottbus|Brandenburg an der Havel',
 'Thüringen': 'Jena|Erfurt|Weimar|Gera',
 'Saarland': 'Saarbrücken|Homburg',
}
STATE_ALIASES = {
 'Bayern': ['Bavaria','Bayern'],
 'Baden-Württemberg': ['Baden-Württemberg','Baden-Wuerttemberg','Baden Wurttemberg'],
 'Hessen': ['Hesse','Hessen'],
 'Nordrhein-Westfalen': ['North Rhine-Westphalia','Nordrhein-Westfalen','NRW'],
 'Sachsen': ['Saxony','Sachsen'],
 'Sachsen-Anhalt': ['Saxony-Anhalt','Sachsen-Anhalt'],
 'Niedersachsen': ['Lower Saxony','Niedersachsen'],
 'Rheinland-Pfalz': ['Rhineland-Palatinate','Rheinland-Pfalz'],
 'Thüringen': ['Thuringia','Thüringen'],
 'Brandenburg': ['Brandenburg'],
 'Schleswig-Holstein': ['Schleswig-Holstein'],
 'Berlin': ['Berlin'], 'Hamburg':['Hamburg'], 'Bremen':['Bremen'],
}
COUNTRY_ALIASES = {'Germany': ['Germany','Deutschland','DEU'],
 'Netherlands':['Netherlands','Nederland'], 'United States':['United States','USA','U.S.A.'],
 'Austria':['Austria','Österreich'], 'Switzerland':['Switzerland','Schweiz'],
 'France':['France'], 'United Kingdom':['United Kingdom','UK'],
 'Belgium':['Belgium'], 'Canada':['Canada'], 'Poland':['Poland'],
 'Portugal':['Portugal'], 'Czechia':['Czech Republic','Czechia','Tschechien'],
 'India':['India'], 'China':['China']}
FOREIGN_CITY_STATES = {
 'Delft': ('Zuid-Holland', 'Netherlands'),
 'Zoetermeer': ('Zuid-Holland', 'Netherlands'),
 'Amsterdam': ('Noord-Holland', 'Netherlands'),
 'Vienna': ('Wien', 'Austria'), 'Wien':('Wien','Austria'),
 'Innsbruck': ('Tirol','Austria'),
 'Zurich': ('Zürich','Switzerland'), 'Zürich': ('Zürich','Switzerland'),
 'Paris': ('Île-de-France','France'),
 'London': ('England','United Kingdom'),
 'Fort Collins': ('Colorado','United States'),
 'Toronto': ('Ontario','Canada'),
 'Warsaw': ('Mazowieckie','Poland'),
 'Coimbra': ('Coimbra','Portugal'),
 'Pilsen': ('Plzeňský kraj','Czechia'), 'Plzeň':('Plzeňský kraj','Czechia'),
 'Shanghai': ('Shanghai','China'), 'Ningbo': ('Zhejiang','China'),
}

# Longer municipality names first, to avoid treating 'Frankfurt am Main' as
# generic 'Frankfurt', and 'Wasserburg am Inn' as 'Wasserburg'.
CITY_STATES = []
for state, places in GERMAN_STATES.items():
    for city in places.split('|'):
        CITY_STATES.append((city, state, 'Germany'))
for city, (region, country) in FOREIGN_CITY_STATES.items():
    CITY_STATES.append((city, region, country))
CITY_STATES.sort(key=lambda x: len(x[0]), reverse=True)


def _contains(text: str, token: str) -> bool:
    return bool(re.search(r'(?<!\w)' + re.escape(token) + r'(?!\w)', text, re.I))


def _country_hint(raw: str):
    for country, aliases in COUNTRY_ALIASES.items():
        if any(_contains(raw, alias) for alias in aliases): return country
    if raw.strip().upper() in ('DE','DEU'): return 'Germany'
    if raw.strip().upper() in ('NL',): return 'Netherlands'
    return None


def _site(raw: str, country_hint: str | None) -> dict:
    part = raw.strip()
    for city, state, country in CITY_STATES:
        if _contains(part, city):
            # Do not overwrite an explicit location city with a source-country
            # hint when the job advertises several countries.
            return {'city': city, 'state': state, 'country': country, 'text': part}
    country = _country_hint(part)
    if not country:
        country = country_hint
    state = None
    if country == 'Germany':
        for region, aliases in STATE_ALIASES.items():
            if any(_contains(part, a) for a in aliases):
                state = region
                break
    # The city must be explicit, not inferred from company or generic
    # 'HQ'/'manufacturing facility' language.
    return {'city': None, 'state': state, 'country': country, 'text': part}


def format_worksites(job: dict) -> dict:
    raw = str(job.get('location') or '').strip()
    source_country = _country_hint(str(job.get('country') or ''))
    # Don't use 'location_status=germany' alone to assert country; it may have
    # been inferred from only one site in a multi-country advertisement.
    parts = [v.strip() for v in re.split(r'\s*;\s*|\s+\|\s+|\s+/\s+', raw) if v.strip()]
    if not parts:
        parts = ['']
    sites = [_site(part, source_country) for part in parts]
    # A raw country-only segment is still a distinct worksite candidate.
    # Do not collapse it into the adjacent city.
    known_countries = sorted({v['country'] for v in sites if v['country']})
    multi = len(sites) > 1
    if multi:
        city, state = None, None
        country = ' / '.join(known_countries) if known_countries else None
    else:
        city, state, country = sites[0]['city'], sites[0]['state'], sites[0]['country']
    unknown_city = any(not s['city'] for s in sites)
    note = ('Multiple advertised locations; confirm the actual worksite' if multi
            else 'City not confirmed from the vacancy location' if unknown_city
            else '')
    return {
        'worksite_city': city, 'worksite_state': state, 'worksite_country': country,
        'worksite_sites': sites, 'worksite_multiple': multi,
        'worksite_note': note, 'worksite_city_verified': not unknown_city,
    }


def main() -> int:
    state = json.loads(STATE.read_text(encoding='utf-8'))
    public = json.loads(PUBLIC.read_text(encoding='utf-8'))
    for job in state.get('jobs', {}).values():
        job.update(format_worksites(job))
    for job in public.get('jobs', []):
        job.update(format_worksites(job))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Added conservative city/state/country labels to {len(public.get('jobs', []))} jobs")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
