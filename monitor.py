#!/usr/bin/env python3
"""Monitor selected public ATS job feeds in Germany; Python standard library only.

For personal job discovery only. This monitor never submits applications.
"""
from __future__ import annotations

import html
import json
import re
import time
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
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


def get_html(url, timeout=25):
    """Read public career-page HTML only; no authentication or browser bypass."""
    req = Request(url, headers={
        "User-Agent": "PersonalJobMonitor/0.3 (public postings)",
        "Accept": "text/html",
    })
    with urlopen(req, timeout=timeout) as response:
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



class PersonioDetailHTML(HTMLParser):
    """Extract public, visible job details and structured JobPosting metadata.

    Do not treat arbitrary page text, navigation, or marketing copy as a job
    description. The parser deliberately leaves incomplete pages title-only.
    """
    BLOCKS = {"h1", "h2", "h3", "h4", "p", "div", "li", "section", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._in_main = False
        self._in_body = False
        self._hidden = 0
        self._in_ld = False
        self._ld_parts = []
        self.json_ld = []
        self._head_tag = None
        self._head_text = []
        self.headings = []
        self.main_text = []
        self.body_text = []

    def _put(self, value):
        if self._in_body:
            self.body_text.append(value)
        if self._in_main:
            self.main_text.append(value)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "main":
            self._in_main = True
        if tag == "body":
            self._in_body = True
        if tag == "script":
            if attributes.get("type", "").lower() == "application/ld+json":
                self._in_ld = True
                self._ld_parts = []
            else:
                self._hidden += 1
        elif tag in ("style", "noscript", "svg"):
            self._hidden += 1
        if tag in ("h1", "h2", "h3", "h4") and not self._hidden:
            self._head_tag = tag
            self._head_text = []
            self._put("\n## ")
        if tag in self.BLOCKS and tag not in ("h1", "h2", "h3", "h4") and not self._hidden:
            self._put("\n")

    def handle_endtag(self, tag):
        if tag == "script":
            if self._in_ld:
                self.json_ld.append("".join(self._ld_parts))
                self._in_ld = False
            elif self._hidden:
                self._hidden -= 1
        elif tag in ("style", "noscript", "svg") and self._hidden:
            self._hidden -= 1
        if tag == self._head_tag:
            heading = " ".join("".join(self._head_text).split())
            if heading:
                self.headings.append((tag, heading))
                self._put("\n")
            self._head_tag = None
            self._head_text = []
        if tag in self.BLOCKS and not self._hidden:
            self._put("\n")
        if tag == "main":
            self._in_main = False
        if tag == "body":
            self._in_body = False

    def handle_data(self, data):
        if self._in_ld:
            self._ld_parts.append(data)
            return
        if self._hidden:
            return
        self._put(data)
        if self._head_tag:
            self._head_text.append(data)


def _jobposting_nodes(obj):
    """Find JobPosting objects in public JSON-LD, including @graph arrays."""
    if isinstance(obj, list):
        for child in obj:
            yield from _jobposting_nodes(child)
    elif isinstance(obj, dict):
        types = obj.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if isinstance(types, list) and "JobPosting" in types:
            yield obj
        if "@graph" in obj:
            yield from _jobposting_nodes(obj["@graph"])


def _personio_location_from_jsonld(posting):
    places = posting.get("jobLocation") or []
    places = places if isinstance(places, list) else [places]
    locations, countries = [], []
    for place in places:
        if not isinstance(place, dict):
            continue
        addr = place.get("address") or {}
        if not isinstance(addr, dict):
            continue
        town = str(addr.get("addressLocality") or "").strip()
        region = str(addr.get("addressRegion") or "").strip()
        country = addr.get("addressCountry") or ""
        if isinstance(country, dict):
            country = country.get("name") or ""
        country = str(country).strip()
        label = ", ".join(x for x in (town, region, country) if x)
        if label:
            locations.append(label)
        if country:
            countries.append(country)
    return "; ".join(dict.fromkeys(locations)), countries[0] if len(set(countries)) == 1 and countries else ""


PERSONIO_SECTION_START = re.compile(
    r"(?:your\s+mission|your\s+role|your\s+tasks|your\s+responsibilities|"
    r"your\s+profile|your\s+qualifications|ihre\s+aufgaben|deine\s+aufgaben|"
    r"das\s+erwartet\s+(?:sie|dich)|was\s+sie\s+erwartet|aufgaben|tätigkeiten|"
    r"anforderungen|ihr\s+profil|dein\s+profil|qualifikationen)", re.I)
PERSONIO_SECTION_END = re.compile(
    r"(?:why\s+us|warum\s+wir|was\s+wir\s+bieten|benefits?|"
    r"kontakt(?:information(?:en)?)?|contact\s+information|about\s+us|über\s+uns|"
    r"jetzt\s+bewerben|apply\s+now)", re.I)


def _personio_section_description(text):
    """Return only task/profile sections, not footer or unrelated page copy."""
    chunks = re.split(r"(?=\n## )", text)
    capture = False
    parts = []
    for chunk in chunks:
        match = re.match(r"\s*##\s*([^\n]+)", chunk)
        heading = match.group(1).strip(" ?!:.\t") if match else ""
        if heading and PERSONIO_SECTION_END.fullmatch(heading):
            if capture:
                break
            continue
        if heading and PERSONIO_SECTION_START.fullmatch(heading):
            capture = True
        if capture:
            parts.append(chunk)
    result = " ".join(" ".join(parts).split())
    return result[:18000] if len(result) >= 120 else ""


def _personio_visible_location(text):
    # The worksite must be explicitly visible near the job heading, not inferred
    # from company address or a location mentioned deep in a job description.
    prefix = text[:900]
    match = re.search(r"\bDE\s*\|\s*Office\s*-\s*([A-ZÄÖÜ][\wÄÖÜäöüß .-]{1,70})", prefix)
    if match:
        place = re.split(r"(?:Full[- ]?time|Part[- ]?time|\bRemote\b|\n|##)", match.group(1))[0].strip(" ,;")
        if place:
            return f"{place}, Germany", "Germany"
    match = re.search(r"\b([A-ZÄÖÜ][\wÄÖÜäöüß .-]{1,60}),\s*(Deutschland|Germany)\b", prefix)
    if match:
        return f"{match.group(1).strip()}, {match.group(2)}", "Germany"
    return "", ""


def enrich_personio_fallback_job(job, page_html):
    """Enrich one fallback item from its public official detail page.

    A title-only item remains title-only unless a recognizable, substantive
    job description is found. Never infer eligibility or worksite from company HQ.
    """
    parser = PersonioDetailHTML()
    parser.feed(page_html)
    # Reject a detail page for another job, such as a redirect to a new listing.
    h1 = next((text for tag, text in parser.headings if tag == "h1"), "")
    if h1 and plain_text(h1).casefold() != plain_text(job["title"]).casefold():
        return job
    description = ""
    location = ""
    country = ""
    posted = None
    for block in parser.json_ld:
        try:
            records = list(_jobposting_nodes(json.loads(block)))
        except (ValueError, TypeError):
            continue
        for record in records:
            ld_title = plain_text(record.get("title") or "")
            if ld_title and ld_title.casefold() != plain_text(job["title"]).casefold():
                continue
            description = plain_text(record.get("description") or "")[:18000]
            location, country = _personio_location_from_jsonld(record)
            posted = record.get("datePosted") or None
            if description:
                break
        if description:
            break
    visible = "".join(parser.main_text) if len("".join(parser.main_text).strip()) > 120 else "".join(parser.body_text)
    if not description:
        description = _personio_section_description(visible)
    if not location:
        location, country = _personio_visible_location(visible)
    if description and len(description) >= 120:
        return {**job, "description": description, "location": location,
                "country": country, "published_at": posted,
                "source_mode": "html_detail"}
    # Location can be useful even when the source lacks job details; missing
    # description still prevents automatic priority email notification.
    return {**job, "location": location, "country": country}


def enrich_personio_fallback(jobs, *, max_pages=30):
    """Fetch detail pages conservatively; preserve failed or incomplete jobs."""
    for index, job in enumerate(jobs[:max_pages]):
        try:
            result = enrich_personio_fallback_job(job, get_html(job["url"], timeout=12))
            jobs[index] = result
        except (HTTPError, URLError, ValueError, TimeoutError, UnicodeError) as exc:
            print(f"DETAIL UNAVAILABLE {job['company']} {job['key']}: {type(exc).__name__}", file=sys.stderr)
        if index < min(len(jobs), max_pages) - 1:
            time.sleep(0.4)  # Be polite to small company career sites.
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


def _safe_rss_job_link(raw, *, base="https://jobs.mytum.de/"):
    """Normalize TUM's relative/HTTP legacy article links, preserving HTTPS external links."""
    link = html.unescape(str(raw or "").strip())
    if not link:
        return ""
    if link.startswith("/") and not link.startswith("//"):
        link = urljoin(base, link)
    parts = urlsplit(link)
    if parts.scheme == "http" and parts.hostname in {"jobs.mytum.de", "portal.mytum.de"}:
        link = parts._replace(scheme="https").geturl()
    return link if urlsplit(link).scheme == "https" and urlsplit(link).netloc else ""


def parse_rss(company, root):
    """Read an official RSS/Atom job feed without treating feed-wide descriptions as job detail evidence."""
    jobs = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    if root.tag.split("}")[-1].lower() == "rss":
        entries = root.findall("./channel/item")
        for entry in entries:
            title = plain_text(entry.findtext("title"))
            link = _safe_rss_job_link(entry.findtext("link"))
            guid = (entry.findtext("guid") or link).strip()
            desc = plain_text(entry.findtext("description"))[:18000]
            published_raw = entry.findtext("pubDate")
            published = None
            if published_raw:
                try:
                    published = parsedate_to_datetime(published_raw).astimezone(timezone.utc).isoformat()
                except (ValueError, TypeError, OverflowError):
                    published = None
            if not title or not link.startswith("https://"):
                continue
            jobs.append({"key": f"rss:{company['slug']}:{guid}", "company": company['name'],
                "title": title, "location": "", "country": "", "description": desc,
                "url": link, "published_at": published, "source_modified_at": None,
                "platform": "rss", "source_mode": "rss_summary"})
    elif root.tag.split("}")[-1].lower() == "feed":
        for entry in root.findall("a:entry", ns):
            title = plain_text(entry.findtext("a:title", default="", namespaces=ns))
            link = _safe_rss_job_link(next((x.attrib.get("href", "") for x in entry.findall("a:link", ns)
                         if x.attrib.get("rel", "alternate") == "alternate"), ""))
            guid = entry.findtext("a:id", default=link, namespaces=ns)
            desc = plain_text(entry.findtext("a:summary", default="", namespaces=ns) or
                              entry.findtext("a:content", default="", namespaces=ns))[:18000]
            published = entry.findtext("a:published", default=None, namespaces=ns) or entry.findtext("a:updated", default=None, namespaces=ns)
            if not title or not link.startswith("https://"):
                continue
            jobs.append({"key": f"rss:{company['slug']}:{guid}", "company": company['name'],
                "title": title, "location": "", "country": "", "description": desc,
                "url": link, "published_at": published, "source_modified_at": None,
                "platform": "rss", "source_mode": "rss_summary"})
    else:
        raise ValueError("Not a recognized RSS or Atom feed")
    # An empty job feed is possible; the root must still have valid channel/feed structure.
    return jobs



def _rss_duplicate_title(value):
    """Ignore capitalization and formatting, not substantive job-title words."""
    return re.sub(r"[^\w]+", " ", str(value or "").casefold(), flags=re.UNICODE).strip()


def _rss_publication_day(job):
    raw = str(job.get("published_at") or "").strip()
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return raw[:10]


def _rss_description_similar(one, two):
    """Require substantial textual overlap before merging separate posting URLs."""
    a = re.sub(r"[^\w]+", " ", str(one or "").casefold(), flags=re.UNICODE).strip()
    b = re.sub(r"[^\w]+", " ", str(two or "").casefold(), flags=re.UNICODE).strip()
    if len(a) < 100 or len(b) < 100:
        return bool(a and a == b and len(a) >= 60)
    return SequenceMatcher(None, a[:1200], b[:1200], autojunk=False).ratio() >= 0.86


def _rss_same_vacancy(one, two):
    if str(one.get("company") or "") != str(two.get("company") or ""):
        return False
    if _rss_duplicate_title(one.get("title")) != _rss_duplicate_title(two.get("title")):
        return False
    if not _rss_publication_day(one) or _rss_publication_day(one) != _rss_publication_day(two):
        return False
    # Distinct employers or laboratories can advertise the same job title on
    # the same day. Description similarity provides a stronger identity check.
    return _rss_description_similar(one.get("description"), two.get("description"))


def deduplicate_rss(jobs, previous_jobs=None):
    """Collapse strongly identical RSS entries, retaining earlier stable IDs.

    Do not deduplicate by title alone: universities may advertise several
    genuinely different openings with identical titles and dates.
    """
    previous_jobs = previous_jobs or {}
    groups = []
    for item in jobs:
        group = next((g for g in groups if _rss_same_vacancy(g[0], item)), None)
        if group is None:
            groups.append([item])
        else:
            group.append(item)
    unique = []
    for group in groups:
        # Previously displayed ID takes priority to protect alert and applied
        # history, irrespective of incoming RSS item order.
        ranked = sorted(group, key=lambda job: (
            0 if job["key"] in previous_jobs else 1,
            str(previous_jobs.get(job["key"], {}).get("first_detected") or "9999"),
            job["key"],
        ))
        chosen = dict(ranked[0])
        group_keys = {str(item["key"]) for item in group}
        # Carry earlier duplicate aliases into the representative record.
        for item in group:
            old = previous_jobs.get(item["key"], {})
            group_keys.update(str(k) for k in old.get("duplicate_keys", []) if k)
        chosen["duplicate_keys"] = sorted(group_keys - {str(chosen["key"])})
        chosen["duplicates_merged"] = max(0, len(group_keys) - 1)
        unique.append(chosen)
    return unique


def title_fingerprint(job):
    title = str(job.get("title") or "").casefold()
    title = re.sub(r"\((?:all genders|m/w/d|f/m/d|m/f/d|w/m/d|d/m/w|all gender[s]?)\)", "", title)
    title = re.sub(r"[^\w]+", " ", title, flags=re.UNICODE)
    company = re.sub(r"[^\w]+", " ", str(job.get("company") or "").casefold())
    return f"{company.strip()}|{title.strip()}"


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
    if provider == "rss":
        feed_url = company.get("feed_url", "")
        if not feed_url.startswith("https://"):
            raise ValueError("Missing official RSS feed URL")
        # Some TUM scientific-only feeds return a valid RSS document containing
        # no usable items. Prefer this specialized feed, then the official all-jobs
        # feed. Never silently report no vacancies if both fail to provide items.
        try:
            jobs = parse_rss(company, get_xml(feed_url))
        except HTTPError as exc:
            if exc.code not in (400, 404, 410) or not company.get("fallback_feed_url"):
                raise
            jobs = []
        except ValueError:
            if not company.get("fallback_feed_url"):
                raise
            jobs = []
        if jobs or not company.get("fallback_feed_url"):
            return jobs
        backup_url = company["fallback_feed_url"]
        if not backup_url.startswith("https://"):
            raise ValueError("Official RSS fallback URL must use HTTPS")
        backup = parse_rss(company, get_xml(backup_url))
        if not backup:
            raise ValueError("Scientific RSS and public RSS both returned zero usable jobs; verify feeds")
        for item in backup:
            item["feed_fallback"] = True
        return backup
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
            # Fetch the public job links first. update() separately enriches
            # their detail pages without altering this stable listing reader.
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


GERMAN_CITIES = ["munich", "münchen", "aachen", "berlin", "hamburg", "frankfurt", "dresden", "stuttgart", "köln", "cologne", "düsseldorf", "essen", "darmstadt", "würzburg", "erlangen", "nürnberg", "nuremberg", "freiburg", "hannover", "bremen", "leipzig", "ulm", "mainz", "regensburg", "tübingen", "alzenau", "karlsruhe", "heidelberg", "ingolstadt", "jena", "kiel", "bonn", "potsdam", "möckern", "magdeburg", "leverkusen", "garching", "bayreuth", "coburg", "konstanz", "rostock", "osnabrück", "augsburg", "halle", "braunschweig", "bielefeld", "fulda", "göttingen", "paderborn", "oberkochen", "aschaffenburg", "hanau", "landsberg", "freising", "planegg", "martinsried", "neuried", "gauting", "penzberg", "geretsried", "inning am ammersee", "wessling", "weßling", "oberpfaffenhofen", "gräfelfing", "kaufbeuren", "burghausen", "wasserburg", "wasserburg am inn", "zwickau", "monheim am rhein", "freiberg", "emmering", "fürstenfeldbruck", "germering", "schwelm", "pforzheim", "maisach", "karlsfeld", "haar", "taufkirchen", "eresing", "esslingen", "heilbronn", "starnberg", "kronberg"]
FOREIGN_COUNTRIES = ["united states", "usa", "colorado", "netherlands", "nederland", "delft", "zoetermeer", "austria", "österreich", "vienna", "wien", "switzerland", "schweiz", "zurich", "zürich", "france", "paris", "united kingdom", "london", "belgium", "brussels", "canada", "toronto", "poland", "warsaw", "polska", "india", "singapore", "coimbra", "portugal", "pilsen", "plzeň", "plzen", "czech republic", "czechia", "tschechien", "china", "shanghai", "ningbo", "innsbruck"]


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
    r"\bwerkstudent", r"\bworking student\b", r"\bstudent\b", r"\binternship\b",
    r"\bpraktikum\b", r"\bpraktikant", r"\bstudent assistant\b",
    r"\bdual(?:es|e|er) studium\b", r"\bduales studium\b",
    r"\bapprentice", r"\blehrling\b", r"\bdual(?:e|er|es) student(?:in)?\b",
    r"\bpromotionsstelle\b", r"\bdoktorand(?:in|en)?\b", r"\bph\.?d\.?\s+(?:student|candidate|position)\b",
    r"\bdoctoral\s+(?:research|student|candidate|position|programme|program)\b",
]
VOCATIONAL_ONLY_TITLES = [
    r"\bchemielaborant(?:in|en|innen)?\b", r"\bpharmakant(?:in|en|innen)?\b",
    r"\bproduktionsmitarbeiter(?:in|innen)?\b", r"\blaborhelfer(?:in|innen)?\b",
    r"\blaborassistent(?:in|en|innen)?\b", r"\bpta\b", r"\bcta\b",
    r"\bmaschinen(?:führer|bediener)(?:in|innen)?\b",
]


# Strictly job-TITLE based exclusions. Do not search descriptions: otherwise
# technical laboratory roles would be hidden for mentioning their HR,
# procurement, or finance colleagues. These are USER PREFERENCES, not legal
# ineligibility findings. The positions remain available in jobs.json.
UNRELATED_JOB_FAMILY_TITLES = [
    r"\b(?:hr|human resources|people\s*(?:&|and)\s*culture|people operations|people partner|head of people)\b",
    r"\b(?:talent acquisition|talent sourcing|recruit(?:er|ing|ment)|personalwesen|personalreferent|personaladministration|personalsachbearbeit|personalentwickl|personalmanagement)\w*\b",
    r"\b(?:finance|financial|finanz\w*|accounting|accountant|accounts payable|accounts receivable|buchhalt\w*|bilanzbuchhalt\w*|controll(?:er|ing)|treasury|payroll|lohnabrechnung|gehaltsabrechnung|tax manager)\b",
    r"\b(?:procurement|purchasing|buyer|buyers|sourcing manager|einkauf\w*|einkäuf\w*|beschaffung\w*|strategic sourcing|supply chain manager|lagerlogistik|warehouse manager)\b",
    r"\b(?:sales|salesperson|sales representative|sales manager|account executive|account manager|business development|commercial manager|marketing|growth manager|market development|social media|public relations|communications manager|event manager|vertrieb\w*|verkauf\w*|kundenakquise)\b",
    r"\b(?:executive assistant|office manager|office administrator|administrative assistant|receptionist|front desk|team assistan\w*|büromanagement|assistenz der geschäftsführung|sachbearbeit\w*|customer support|customer success)\b",
    r"\b(?:legal counsel|lawyer|rechtsanwalt|patent attorney|patentanwalt|paralegal|compliance officer|contract manager|steuerberater)\b",
    r"\b(?:software engineer|software developer|frontend|front-end|backend|back-end|fullstack|full-stack|devops|it support|it administrator|erp implementation|embedded software|data engineer)\b",
    # Software SDK roles do not overlap with experimental chemistry.
    r"\b(?:python|java|javascript|typescript|c\+\+|sdk)\s+(?:software\s+)?(?:sdk\s+)?(?:engineer|developer|architect|programmer)\b",
    r"\b(?:sdk|api)\s+(?:integration\s+)?(?:engineer|developer|architect)\b",
    # Design-only photonics, avionics, algorithms, and electrical architectures.
    r"\b(?:photonic(?:s)?\s+(?:integrated\s+)?circuit\s+design(?:er)?|photonic(?:s)?\s+circuit|pic\s+design(?:er)?)\b",
    r"\b(?:algorithm(?:s)?\s+engineer|engineer\s+[-–]\s+algorithms|battery\s+algorithms|control\s+algorithms)\b",
    r"\b(?:electronics?\s+(?:systems?\s+)?architect|architect\s+(?:of\s+)?electronics?|hardware\s+architect|avionics\s+architect|fpga\s+(?:engineer|architect|designer))\b",
    r"\b(?:pcb\s+(?:layout\s+)?(?:engineer|designer|architect)|embedded\s+(?:systems?\s+)?architect|firmware\s+(?:engineer|developer))\b",
    r"\b(?:hardware\s+systems?\s+manager|head\s+of\s+(?:electronics|software|it|avionics))\b",
    r"\b(?:unsolicited application|spontaneous application|open application|initiativbewerbung|talent pool|general interest pool)\b",
]


MOTOR_DOMAIN_TITLE = re.compile(r"\b(?:electric\s+motors?|elektromotor\w*|electric\s+drive\s+systems?|electric\s+motoren?|e[- ]?motoren?)\b", re.I)
CHEMICAL_ROLE_TITLE = re.compile(r"\b(?:chem(?:istry|ical|ist|ie|iker)\w*|material\w*|werkstoff\w*|coating\w*|beschicht\w*|polymer\w*|surface\w*|oberfl[aä]ch\w*|formulat\w*|formulier\w*|nanopartic\w*|nanopartik\w*)\b", re.I)


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
    # Exclude motor/robotics production engineering, but retain chemistry and
    # materials roles explicitly working on motor coatings or insulation.
    if MOTOR_DOMAIN_TITLE.search(title) and not CHEMICAL_ROLE_TITLE.search(title):
        return {"career_track": "unrelated", "hide_by_default": True,
                "preference_note": "Electric-motor engineering rather than chemical/materials development"}
    if any(re.search(p, title, re.IGNORECASE) for p in UNRELATED_JOB_FAMILY_TITLES):
        return {"career_track": "unrelated", "hide_by_default": True,
                "preference_note": "Excluded job family by preference (not an eligibility determination)"}
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
    unrelated = (any(x in title for x in NON_TARGET_TITLES)
                 or _has_any_patterns(title, UNRELATED_JOB_FAMILY_TITLES))
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
            rss_duplicates_removed = 0
            if company["platform"] == "rss":
                raw_rss_count = len(seen)
                seen = deduplicate_rss(seen, state["jobs"])
                rss_duplicates_removed = raw_rss_count - len(seen)
            # When an earlier misconfigured RSS feed reported 0, treat the
            # recovered batch as its first baseline, not new email alerts.
            if (company["platform"] == "rss" and entry.get("count") == 0
                    and any(j.get("feed_fallback") for j in seen)):
                was_initialized = False
            if company["platform"] == "personio" and any(j.get("source_mode") == "html_fallback" for j in seen):
                seen = enrich_personio_fallback(seen)
            keys = set()
            for job in seen:
                if job.get("location") is None:
                    job["location"] = ""
                if location_status(job) == "outside":
                    continue
                key = job["key"]
                keys.add(key)
                old = state["jobs"].get(key)
                was_reopened = bool(old and old.get("active") is False)
                job.update({
                    "first_detected": old["first_detected"] if old else at,
                    "at_startup": old["at_startup"] if old else not was_initialized,
                    "last_seen": at,
                    "active": True,
                    "location_status": location_status(job),
                    "fingerprint": title_fingerprint(job),
                    # A confirmed reappearance requires a previously successful scan
                    # where this exact posting key had disappeared.
                    "reopen_count": (old or {}).get("reopen_count", 0) + (1 if was_reopened else 0),
                    "reopened_at": at if was_reopened else (old or {}).get("reopened_at"),
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
                                     "source_mode": ("public_rss_fallback" if any(j.get("feed_fallback") for j in seen) else
                                                     "html_fallback" if any(j.get("source_mode") == "html_fallback" for j in seen) else
                                                     "html_detail" if any(j.get("source_mode") == "html_detail" for j in seen) else "structured_feed"),
                                     "details_extracted": sum(j.get("source_mode") == "html_detail" for j in seen),
                                     "title_only_count": sum(j.get("source_mode") == "html_fallback" for j in seen),
                                     "duplicates_removed": rss_duplicates_removed}
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
