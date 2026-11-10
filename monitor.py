#!/usr/bin/env python3
"""Monitor selected public ATS job feeds in Germany; Python standard library only.

For personal job discovery only. This monitor never submits applications.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

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
    # Some Greenhouse boards return nested HTML entities. Decode before parsing
    # so tags do not leak into keyword screening and the published JSON.
    raw = str(value or "")
    for _ in range(2):
        decoded = html.unescape(raw)
        if decoded == raw:
            break
        raw = decoded
    p = PlainHTML()
    p.feed(raw)
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


def get_xml(url):
    # Personio's public XML feed can be disabled by the employer; treat that as
    # a source error, not as proof the employer has zero open vacancies.
    req = Request(url, headers={"User-Agent": "PersonalJobMonitor/0.2 (public postings)", "Accept": "application/xml,text/xml"})
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("Personio XML feed too large")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid Personio XML feed: {exc}") from exc


def get_html(url):
    """Read public career-page HTML only; no authentication or browser bypass."""
    req = Request(url, headers={
        "User-Agent": "PersonalJobMonitor/0.3 (public postings)",
        "Accept": "text/html",
    })
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError("Personio career page too large")
    return raw.decode("utf-8", errors="replace")


class PersonioJobLinks(HTMLParser):
    """Conservative fallback for public Personio pages without enabled XML."""
    def __init__(self, careers_url):
        super().__init__(convert_charrefs=True)
        self.careers_url = careers_url
        self.host = urlsplit(careers_url).netloc.casefold()
        self.active = None
        self.heading = False
        self.items = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and self.active is None:
            url = urljoin(self.careers_url, attrs.get("href", ""))
            parts = urlsplit(url)
            match = re.fullmatch(r"/job/(\d+)(?:/.*)?", parts.path.rstrip("/"))
            if (match and parts.scheme == "https"
                    and parts.netloc.casefold() == self.host):
                self.active = {"id": match.group(1), "url": url,
                               "text": [], "headings": []}
                self.heading = False
        elif self.active is not None and tag in ("h1", "h2", "h3", "h4"):
            self.heading = True
        elif self.active is not None and tag in ("br", "div", "span", "p", "li"):
            self.active["text"].append(" ")

    def handle_endtag(self, tag):
        if self.active is not None and tag in ("h1", "h2", "h3", "h4"):
            self.heading = False
        if tag == "a" and self.active is not None:
            item = self.active
            item["title"] = " ".join(" ".join(item["headings"] or item["text"]).split())
            if item["title"]:
                self.items.setdefault(item["id"], item)
            self.active = None
            self.heading = False

    def handle_data(self, data):
        if self.active is not None:
            self.active["text"].append(data)
            if self.heading:
                self.active["headings"].append(data)


def parse_personio_html(company, page_html):
    """Fallback never treats an unrecognized page as an empty job board."""
    parser = PersonioJobLinks(company["careers_url"])
    parser.feed(page_html)
    if not parser.items:
        raise ValueError("No public Personio job links found; do not infer zero jobs")
    jobs = []
    for job_id, item in parser.items.items():
        jobs.append({
            "key": f"personio:{company['slug']}:{job_id}",
            "company": company["name"],
            "title": item["title"],
            "location": "",  # Cannot infer worksite from employer headquarters.
            "country": "",
            "description": "", # Full criteria not available in fallback.
            "url": item["url"],
            "published_at": None,
            "source_modified_at": None,
            "platform": "personio",
            "source_mode": "html_fallback",
        })
    return jobs


def normalize_personio(company, position):
    def field(path):
        node = position.find(path)
        return " ".join(" ".join(node.itertext()).split()) if node is not None else ""

    job_id = field("id")
    title = field("name")
    if not job_id or not title:
        raise ValueError("Personio position missing id or name")
    parts = []
    for item in position.findall("./jobDescriptions/jobDescription"):
        section = " ".join(item.findtext("name", default="").split())
        value = item.find("value")
        description = plain_text(" ".join(value.itertext())) if value is not None else ""
        if description:
            parts.append((section + ": " if section else "") + description)
    # Personio's 'createdAt' is an ATS creation time, not a guaranteed public
    # posting date. It must never be shown as 'first published'.
    created = field("createdAt") or None
    return {
        "key": f"personio:{company['slug']}:{job_id}",
        "company": company["name"],
        "title": title,
        "location": field("office") or field("location"),
        "country": field("country"),
        "description": " ".join(parts)[:18000],
        "url": company["careers_url"].rstrip("/") + "/job/" + quote(job_id, safe=""),
        "published_at": None,
        "source_created_at": created,
        "source_modified_at": None,
        "platform": "personio",
        "employment_type": field("employmentType"),
    }


def parse_personio(company, root):
    if root.tag not in ("workzag-jobs", "{https://personio.com}workzag-jobs"):
        raise ValueError("Unexpected Personio XML root (feed may be disabled)")
    # A valid empty feed is an authentic zero-jobs state.
    return [normalize_personio(company, p) for p in root.findall("position")]


def normalize_softgarden(company, element):
    # softgarden's publicly advertised JSON-LD DataFeed uses DataFeedItem.item.
    # A career site can include a single Place or multiple Place objects.
    item = element.get("item") if isinstance(element, dict) else None
    if not isinstance(item, dict) or not item.get("title"):
        raise ValueError("Invalid softgarden JobPosting item")
    ident = item.get("identifier") or {}
    job_id = ident.get("value") if isinstance(ident, dict) else None
    job_url = item.get("url")
    if not isinstance(job_url, str) or not job_url.startswith("https://"):
        raise ValueError("Missing valid softgarden job URL")
    if job_id is None:
        # Stable official job URLs are an acceptable fallback key.
        job_id = job_url

    place_list = item.get("jobLocation") or []
    if isinstance(place_list, dict):
        place_list = [place_list]
    locations, countries = [], []
    for place in place_list:
        if not isinstance(place, dict):
            continue
        address = place.get("address") or {}
        if not isinstance(address, dict):
            continue
        city = str(address.get("addressLocality") or "").strip()
        region = str(address.get("addressRegion") or "").strip()
        country = str(address.get("addressCountry") or "").strip()
        locations.append(", ".join(x for x in (city, region, country) if x))
        if country:
            countries.append(country)
    location = "; ".join(dict.fromkeys(x for x in locations if x))
    if not location:
        # A missing workplace must remain uncertain, not assumed to be Germany.
        location = str(item.get("jobLocationType") or "")
    return {
        "key": f"softgarden:{company['slug']}:{job_id}",
        "company": company["name"],
        "title": str(item["title"]),
        "location": location,
        "country": countries[0] if len(set(countries)) == 1 else "",
        "description": plain_text(item.get("description") or "")[:18000],
        "url": job_url,
        "published_at": item.get("datePosted"),
        "source_modified_at": element.get("dateModified"),
        "platform": "softgarden",
    }


def parse_softgarden(company, feed):
    if not isinstance(feed, dict) or feed.get("@type") != "DataFeed":
        raise ValueError("Unexpected softgarden job feed format")
    elements = feed.get("dataFeedElement")
    if not isinstance(elements, list):
        raise ValueError("softgarden feed is missing dataFeedElement array")
    # An actual empty feed is a valid zero-positions result.
    return [normalize_softgarden(company, x) for x in elements]


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
    if provider == "softgarden":
        # Public JSON-LD feed confirmed at the employer's own softgarden site.
        # Do not use authenticated softgarden APIs or third-party aggregators.
        feed_url = company.get("feed_url")
        if not isinstance(feed_url, str) or not feed_url.startswith("https://"):
            raise ValueError("Missing verified softgarden feed_url")
        return parse_softgarden(company, get_json(feed_url))
    if provider == "personio":
        # Feed hostname is already grounded in the official employer career URL.
        url = company["careers_url"].rstrip("/") + "/xml?language=de"
        try:
            return parse_personio(company, get_xml(url))
        except HTTPError as exc:
            if exc.code != 404:
                raise  # Do not circumvent access restrictions.
            # Some employers publish a career page but disable the optional XML feed.
            # Read publicly linked vacancies and flag that descriptions are unavailable.
            return parse_personio_html(company, get_html(company["careers_url"]))
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


GERMAN_CITIES = ["munich", "münchen", "aachen", "berlin", "hamburg", "frankfurt", "dresden", "stuttgart", "köln", "cologne", "düsseldorf", "essen", "darmstadt", "würzburg", "erlangen", "nürnberg", "nuremberg", "freiburg", "hannover", "bremen", "leipzig", "ulm", "mainz", "regensburg", "tübingen", "alzenau", "karlsruhe", "heidelberg", "ingolstadt", "jena", "kiel", "bonn", "potsdam", "möckern", "magdeburg", "leverkusen", "garching", "bayreuth", "coburg", "konstanz", "rostock", "osnabrück", "augsburg", "halle", "braunschweig", "bielefeld", "fulda", "göttingen", "paderborn", "oberkochen", "aschaffenburg", "hanau", "landsberg", "freising", "planegg", "martinsried", "neuried", "gauting", "penzberg", "geretsried", "inning am ammersee", "wessling", "weßling", "oberpfaffenhofen", "gräfelfing", "kaufbeuren", "burghausen", "wasserburg", "wasserburg am inn", "zwickau", "monheim am rhein", "freiberg", "emmering", "fürstenfeldbruck", "germering", "schwelm", "pforzheim", "maisach"]
FOREIGN_COUNTRIES = ["united states", "usa", "colorado", "netherlands", "nederland", "delft", "zoetermeer", "austria", "österreich", "vienna", "wien", "switzerland", "schweiz", "zurich", "zürich", "france", "paris", "united kingdom", "london", "belgium", "brussels", "canada", "toronto", "poland", "warsaw", "polska", "india", "singapore", "coimbra", "portugal"]


def location_status(job):
    country = str(job.get("country") or "").strip().casefold()
    loc = str(job.get("location") or "").casefold()
    german_site = any(x in loc for x in GERMAN_CITIES) or any(x in loc for x in ["germany", "deutschland"])
    foreign_site = any(x in loc for x in FOREIGN_COUNTRIES)
    # Multi-country or ambiguous listings require worksite verification.
    if german_site and foreign_site:
        return "verify_location"
    if foreign_site:
        return "outside"
    if german_site:
        return "germany"
    if country in ("germany", "de", "deu"):
        return "germany"
    if country:
        return "outside"
    return "verify_location"

# Preference filter is not a hiring-eligibility decision. All vacancies remain
# in jobs.json for optional manual review; the website hides the following by default.
TRAINING_TITLES = [
    r"\bausbildung\b", r"\bauszubild", r"\bschülerpraktikum\b",
    r"\bwerkstudent", r"\bworking student\b", r"\binternship\b",
    r"\bpraktikum\b", r"\bpraktikant", r"\bstudent assistant\b",
    r"\bdual(?:es|e|er) studium\b", r"\bduales studium\b",
    r"\bapprentice", r"\blehrling\b", r"\bdual(?:e|er|es) student(?:in)?\b",
]
VOCATIONAL_ONLY_TITLES = [
    r"\bchemielaborant(?:in|en|innen)?\b", r"\bpharmakant(?:in|en|innen)?\b",
    r"\bproduktionsmitarbeiter(?:in|innen)?\b", r"\blaborhelfer(?:in|innen)?\b",
    r"\blaborassistent(?:in|en|innen)?\b", r"\bpta\b", r"\bcta\b",
    r"\bmaschinen(?:führer|bediener)(?:in|innen)?\b",
]


def qualification_preference(job):
    title = str(job.get("title") or "")
    if any(re.search(p, title, re.IGNORECASE) for p in TRAINING_TITLES):
        return {"career_track": "training", "hide_by_default": True,
                "preference_note": "Training, student or apprenticeship position"}
    # Personio records some training jobs under employmentType=trainee.
    if str(job.get("employment_type") or "").lower() == "intern":
        return {"career_track": "training", "hide_by_default": True,
                "preference_note": "Internship listing"}
    if any(re.search(p, title, re.IGNORECASE) for p in VOCATIONAL_ONLY_TITLES):
        return {"career_track": "vocational", "hide_by_default": True,
                "preference_note": "Vocationally oriented job title; verify degree requirement"}
    return {"career_track": "professional_or_unknown", "hide_by_default": False,
            "preference_note": "Degree requirement not automatically verified"}


# Rule-based screening is only a triage aid, NOT a validated job-fit judgment.
# Prioritize overlap in technical work, not generic "materials" or "process" words.
SIGNALS = {
    "Nanoparticles / silica": ["nanoparticle", "nanopartikel", "silica", "sio2", "sio₂", "sol-gel", "aerogel", "kolloid", "colloid", "particle synthesis", "partikelsynthese"],
    "Formulation / dispersions": ["formulation", "formulierung", "dispersion", "emulsion", "suspension", "surfactant", "tensid", "stabilizer", "stabilisator", "recipe formulation", "compounding trials"],
    "Characterization": ["dls", "zeta potential", "zetapotenzial", "ft-ir", "ftir", "tga", "bet surface", "electron microscopy", "elektronenmikroskop", "scanning electron microscopy", "sem analysis", "particle characterization", "materialcharakterisierung", "material characterization"],
    "Materials / surfaces": ["materials science", "materialwissenschaft", "oberflächenchemie", "surface functionalization", "surface modification", "materialentwicklung", "polymer", "cellulose", "zellulose", "material compounds"],
    "Process / DoE": ["design of experiments", "versuchsplanung", "process development", "prozessentwicklung", "process optimization", "prozessoptimierung", "scale-up", "statistical experiment", "doe", "sol gel"],
}

# Do not promote student, unrelated occupations or domain-specific senior roles
# merely because generic technical words occur in the full job description.
JOB_BLOCKERS = ["working student", "werkstudent", "praktikant", "internship", "praktikum", "student assistant", "graduate internship", "mandatory internship"]
NON_TARGET_TITLES = [
    "finance", "account", "procurement", "einkäufer", "einkäuferin", "purchasing", "sales", "marketing", "recruit", "human resources", "people & culture", "people operations", "talent", "legal", "treasury", "controller", "business development", "software", "devops", "electrical", "electronic", "embedded", "mechanical", "structural", "aerodynamic", "aircraft performance", "pcb", "project manager - erp", "erp implementation", "automation engineer - facilities", "high-voltage systems", "battery algorithms", "bms hardware", "hse officer", "systems engineer", "product qualification", "senior quality manager", "grant projects", "general interest pool", "unsolicited application", "initiativbewerbung",
]
# Specific subjects where the documented CV has close hands-on overlap.
DIRECT_TITLE = [
    r"nanopart", r"silica", r"sio2", r"aerogel", r"colloid", r"kolloid", r"dispers", r"formulat", r"formulier", r"chemical develop", r"chemiker", r"material compounds", r"particle character", r"sem technician", r"sem operator", r"materialcharakteris",
]
GENERAL_TECH_TITLE = [
    r"material", r"werkstoff", r"chem", r"scientist", r"research", r"r&d", r"process", r"prozess", r"developer", r"entwick", r"application", r"applikation", r"technician", r"techniker", r"labor", r"inspection", r"metrolog", r"microscop", r"analyt",
]
SENIOR_TITLE = [r"\bsenior\b", r"\bsmts\b", r"\bprincipal\b", r"\bdirector\b", r"\bhead of\b", r"\bteam lead\b", r"\bchief\b", r"\bvp\b", r"\bexpert\b"]


def _has_any_patterns(text, patterns):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def triage(job):
    title = str(job.get("title") or "").casefold()
    body = plain_text(job.get("description") or "").casefold()
    topics = [group for group, words in SIGNALS.items()
              if any(word.casefold() in title or word.casefold() in body for word in words)]
    direct = _has_any_patterns(title, DIRECT_TITLE)
    general = _has_any_patterns(title, GENERAL_TECH_TITLE)
    senior = _has_any_patterns(title, SENIOR_TITLE)
    student = any(x in title for x in JOB_BLOCKERS)
    unrelated = any(x in title for x in NON_TARGET_TITLES)
    # Hard requirements demonstrably absent from the documented experience.
    # This list is deliberately conservative and is not exhaustive.
    critical_gap = any(re.search(pattern, body) for pattern in (
        r"8[–\-]10 years of experience in aerospace",
        r"8\+ years of.*isotope exchange",
        r"background in isotope exchange chemistry",
        r"5\+ years of experience in semiconductor inspection",
        r"proven experience on at least one aircraft development program",
        r"at least one aircraft development program",
        r"hands-on experience with unpatterned wafer inspection",
    ))

    notes = []
    if student:
        band = "Not target"
        notes.append("Student or internship position")
    elif unrelated:
        band = "Low"
        notes.append("Different core profession")
    elif critical_gap:
        band = "Low"
        notes.append("Essential sector-specific experience not documented")
    elif senior:
        band = "Possible" if direct and len(topics) >= 2 else "Low"
        notes.append("Senior experience requirements require verification")
    elif direct and len(topics) >= 2:
        band = "Review first"
        notes.append("Strong overlap in title and technical tasks; verify full requirements")
    elif (direct and topics) or (general and len(topics) >= 2):
        band = "Possible"
        notes.append("Related technical work; assess essential requirements")
    else:
        band = "Low"
        notes.append("Insufficient direct technical overlap")

    return {"match_band": band, "matched_topics": topics, "triage_note": "; ".join(notes)}


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
                job.update(qualification_preference(job))
                if job["hide_by_default"]:
                    job["match_band"] = "Not target"
                    job["triage_note"] = job["preference_note"]
                state["jobs"][key] = job
            # Only mark absent after a successful request. A failed source must retain its jobs.
            for key, job in state["jobs"].items():
                if job.get("company") == name and key not in keys:
                    job["active"] = False
            state["sources"][name] = {"initialized": True, "status": "ok", "last_checked": at, "count": len(keys), "careers_url": company["careers_url"],
                                     "source_mode": "html_fallback" if any(j.get("source_mode") == "html_fallback" for j in seen) else "structured_feed"}
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


if __name__ == "__main__":
    sys.exit(main())
