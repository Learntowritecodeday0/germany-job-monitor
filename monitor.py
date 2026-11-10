#!/usr/bin/env python3
"""Monitor selected public ATS job feeds in Germany; Python standard library only.

For personal job discovery only. This monitor never submits applications.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "state.json"
OUTPUT = ROOT / "docs" / "jobs.json"
CONFIG = ROOT / "config" / "companies.json"


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3"):
            self.words.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        elif tag in ("p", "div", "li", "h1", "h2", "h3"):
            self.words.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.words.append(data)


def plain_text(value):
    p = PlainHTML()
    p.feed(str(value or ""))
    return " ".join(html.unescape("".join(p.words)).split())


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_json(url):
    req = Request(url, headers={"User-Agent": "PersonalJobMonitor/0.1 (public postings)", "Accept": "application/json"})
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        raw = response.read(8_000_000)
        return json.loads(raw.decode("utf-8"))


def fetch_company(company):
    slug = quote(company["slug"], safe="")
    provider = company["platform"]
    if provider == "greenhouse_eu":
        url = f"https://boards.eu.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        data = get_json(url)
        items = data.get("jobs")
        if not isinstance(items, list):
            raise ValueError("Unexpected Greenhouse response: missing jobs array")
        return [normalize_greenhouse(company, x) for x in items]
    if provider == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        data = get_json(url)
        items = data.get("jobs")
        if not isinstance(items, list):
            raise ValueError("Unexpected Greenhouse response: missing jobs array")
        return [normalize_greenhouse(company, x) for x in items]
    if provider == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        data = get_json(url)
        items = data.get("jobs")
        if not isinstance(items, list):
            raise ValueError("Unexpected Ashby response: missing jobs array")
        return [normalize_ashby(company, x) for x in items if x.get("isListed", True)]
    raise ValueError(f"Unsupported platform: {provider}")


def normalize_greenhouse(company, item):
    location = item.get("location") or {}
    loc = location.get("name", "") if isinstance(location, dict) else str(location)
    return {
        "key": f"{company['platform']}:{company['slug']}:{item.get('id')}",
        "company": company["name"],
        "title": item.get("title", "Untitled"),
        "location": loc,
        "country": "",
        "description": plain_text(item.get("content", ""))[:18000],
        "url": item.get("absolute_url") or company["careers_url"],
        "published_at": item.get("first_published"),
        "source_modified_at": item.get("updated_at"),
        "platform": company["platform"],
    }


def normalize_ashby(company, item):
    address = item.get("address") or {}
    postal = address.get("postalAddress") or {}
    loc = item.get("location", "")
    extra = "; ".join(x.get("location", "") for x in item.get("secondaryLocations", []) if isinstance(x, dict))
    if extra:
        loc = f"{loc}; {extra}"
    url = item.get("jobUrl") or company["careers_url"]
    return {
        "key": f"ashby:{company['slug']}:{url}",
        "company": company["name"],
        "title": item.get("title", "Untitled"),
        "location": loc,
        "country": postal.get("addressCountry", ""),
        "description": plain_text(item.get("descriptionPlain") or item.get("descriptionHtml", ""))[:18000],
        "url": url,
        "published_at": item.get("publishedAt"),
        "source_modified_at": None,
        "platform": "ashby",
    }


GERMAN_CITIES = ["munich", "münchen", "aachen", "berlin", "hamburg", "frankfurt", "dresden", "stuttgart", "köln", "cologne", "düsseldorf", "essen", "darmstadt", "würzburg", "erlangen", "nürnberg", "nuremberg", "freiburg", "hannover", "bremen", "leipzig", "ulm", "mainz", "regensburg", "tübingen", "alzenau", "karlsruhe", "heidelberg", "ingolstadt", "jena", "kiel", "bonn", "potsdam", "möckern", "magdeburg", "leverkusen", "garching", "bayreuth", "coburg", "konstanz", "rostock", "osnabrück", "augsburg", "halle", "braunschweig", "bielefeld", "fulda", "göttingen", "paderborn", "oberkochen", "aschaffenburg", "hanau", "landsberg", "freising", "planegg"]
FOREIGN_COUNTRIES = ["united states", "usa", "colorado", "netherlands", "nederland", "delft", "zoetermeer", "austria", "österreich", "vienna", "wien", "switzerland", "schweiz", "zurich", "zürich", "france", "paris", "united kingdom", "london", "belgium", "brussels", "canada", "toronto", "poland", "warsaw", "polska", "india", "singapore"]


def location_status(job):
    country = str(job.get("country") or "").strip().casefold()
    loc = str(job.get("location") or "").casefold()
    # Mixed-location posts should be reviewed instead of silently filtered out.
    if any(x in loc for x in GERMAN_CITIES) or any(x in loc for x in ["germany", "deutschland"]):
        return "germany"
    if country in ("germany", "de", "deu"):
        return "germany"
    if country and country not in ("germany", "de", "deu"):
        return "outside"
    if any(x in loc for x in FOREIGN_COUNTRIES):
        return "outside"
    return "verify_location"

# Job-text signals are only a triage aid, NOT a hiring-fit assessment.
SIGNALS = {
    "Nanoparticles / silica": ["nanoparticle", "nanopartikel", "silica", "siO2", "sio₂", "sol-gel", "aerogel", "kolloid", "colloid", "particle synthesis", "partikelsynthese"],
    "Formulation / dispersions": ["formulation", "formulierung", "dispersion", "emulsion", "suspension", "surfactant", "tensid", "stabilizer", "stabilisator"],
    "Characterization": ["dls", "zeta potential", "zetapotenzial", "ft-ir", "ftir", "tga", "bet surface", "electron microscopy", "elektronenmikroskop", "particle characterization", "materialcharakterisierung", "material characterization"],
    "Materials / surfaces": ["materials science", "materialwissenschaft", "oberflächenchemie", "surface functionalization", "surface modification", "materialentwicklung", "polymer", "cellulose", "zellulose"],
    "Process / DoE": ["design of experiments", "versuchsplanung", "process development", "prozessentwicklung", "process optimization", "prozessoptimierung", "scale-up", "doe", "sol gel"],
}
JOB_BLOCKERS = ["working student", "werkstudent", "praktikant", "internship", "praktikum", "student assistant", "graduate internship"]
SENIORITY = ["principal", "director", "head of", "vice president", "vp ", "chief ", "staff engineer", "senior manager"]
NONTECHNICAL_TITLE = ["finance", "accounting", "business development", "recruiter", "recruiting", "human resources", "people partner", "sales manager", "procurement", "legal counsel", "marketing", "software engineer", "electrical engineer", "mechanical engineer"]


def triage(job):
    title = (job.get("title") or "").casefold()
    body = (job.get("description") or "").casefold()
    topics = []
    for group, words in SIGNALS.items():
        if any(w.casefold() in title or w.casefold() in body for w in words):
            topics.append(group)
    title_relevant = any(w.casefold() in title for words in SIGNALS.values() for w in words)
    if any(x in title for x in JOB_BLOCKERS):
        band = "Not target"
    elif any(x in title for x in SENIORITY) or any(x in title for x in NONTECHNICAL_TITLE):
        band = "Low"
    elif len(topics) >= 2 and title_relevant:
        band = "Review first"
    elif len(topics) >= 2 or title_relevant:
        band = "Possible"
    else:
        band = "Low"
    return {"match_band": band, "matched_topics": topics}


def update(config, state, at):
    state = json.loads(json.dumps(state))
    state.setdefault("jobs", {})
    state.setdefault("sources", {})
    state["schema"] = 1
    for company in config["companies"]:
        name = company["name"]
        entry = state["sources"].get(name, {})
        was_initialized = bool(entry.get("initialized"))
        try:
            seen = fetch_company(company)
            keys = set()
            for job in seen:
                if job.get("location") is None:
                    job["location"] = ""
                if location_status(job) == "outside":
                    continue
                key = job["key"]
                keys.add(key)
                old = state["jobs"].get(key)
                job.update({
                    "first_detected": old["first_detected"] if old else at,
                    "at_startup": old["at_startup"] if old else not was_initialized,
                    "last_seen": at,
                    "active": True,
                    "location_status": location_status(job),
                })
                job.update(triage(job))
                state["jobs"][key] = job
            # Only mark absent after a successful request. A failed source must retain its jobs.
            for key, job in state["jobs"].items():
                if job.get("company") == name and key not in keys:
                    job["active"] = False
            state["sources"][name] = {"initialized": True, "status": "ok", "last_checked": at, "count": len(keys), "careers_url": company["careers_url"]}
            print(f"OK {name}: {len(keys)} German/unknown-location listings")
        except (HTTPError, URLError, ValueError, KeyError, TimeoutError, json.JSONDecodeError) as exc:
            state["sources"][name] = {**entry, "status": "error", "last_checked": at, "error": f"{type(exc).__name__}: {str(exc)[:160]}", "careers_url": company["careers_url"]}
            print(f"ERROR {name}: {exc}", file=sys.stderr)
    return state


def public_data(state, at):
    jobs = [job for job in state["jobs"].values() if job.get("active")]
    jobs.sort(key=lambda x: (x.get("first_detected") or "", x.get("company") or ""), reverse=True)
    return {"last_checked": at, "notice": "Keyword triage only; verify essential requirements and location manually. 'First detected' is not the original publication date.", "jobs": jobs, "sources": [{"name": k, **v} for k, v in state["sources"].items()]}


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"jobs": {}, "sources": {}}
    at = now_utc()
    state = update(config, state, at)
    STATE.parent.mkdir(exist_ok=True, parents=True)
    OUTPUT.parent.mkdir(exist_ok=True, parents=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT.write_text(json.dumps(public_data(state, at), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not any(source.get("status") == "ok" for source in state["sources"].values()):
        print("WARNING: No source returned successfully. Check workflow logs.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
