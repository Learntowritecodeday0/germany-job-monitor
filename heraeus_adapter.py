"""Conservative public HTML reader for Heraeus's Radancy category listings.

Scope is limited to official public R&D and Lab & Analytics category pages.
No JS execution, authenticated API, job-board workaround, or inferred posting dates.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from career_adapters import visible, trim_job_description


class HeraeusJobLinks(HTMLParser):
    """Read only /en/job/<city>/<title>/3105/<id> links on the official host."""
    PATH = re.compile(r"^/en/job/([a-z0-9-]+)/[^/?#]+/3105/(\d+)/?$", re.I)

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.host = urlsplit(base_url).hostname
        self.anchor = None
        self.entries = {}

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        url = urljoin(self.base_url, href)
        parts = urlsplit(url)
        m = self.PATH.fullmatch(parts.path)
        if m and parts.scheme == "https" and parts.hostname == self.host:
            self.anchor = {"id": m.group(2), "city_slug": m.group(1).casefold(),
                           "url": parts._replace(query="", fragment="").geturl(),
                           "text": []}

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            entry = self.anchor
            entry["title"] = " ".join("".join(entry["text"]).split())
            if len(entry["title"]) >= 4:
                self.entries.setdefault(entry["id"], entry)
            self.anchor = None


def parse_heraeus_category(company, page_html):
    parser = HeraeusJobLinks(company["careers_url"])
    parser.feed(page_html)
    if not parser.entries:
        # We cannot distinguish an empty category from a changed/blocked site
        # unless the page explicitly declares zero postings.
        _, plain = visible(page_html)
        if re.search(r"\b(?:0\s+(?:found\s+)?(?:research|lab|analytics|jobs)|no\s+jobs\s+found)\b", plain, re.I):
            return []
        raise ValueError("Heraeus category page contained no recognized official job links")

    cities = company.get("german_cities")
    if not isinstance(cities, dict) or not cities:
        raise ValueError("Heraeus source requires verified German city slugs")

    jobs = []
    for item in parser.entries.values():
        city = cities.get(item["city_slug"])
        # The public category pages also list foreign jobs. Only explicitly
        # confirmed German worksites are in scope. Unlisted cities are skipped.
        if not city:
            continue
        jobs.append({
            "key": f"heraeus_categories:{company['slug']}:{item['id']}",
            "company": company["name"], "title": item["title"],
            "location": city + ", Germany", "country": "Germany",
            "description": "", "url": item["url"],
            "published_at": None, "source_modified_at": None,
            "platform": "heraeus_categories",
            "source_mode": "recent_title_only",
            "source_coverage": "partial_category_window",
        })
    return jobs


def enrich_heraeus_job(job, detail_html):
    """Extract explicit tasks and requirements, never infer missing details."""
    parsed, plain = visible(detail_html)
    title = " ".join("".join(parsed.h1).split())
    # Verify that fetched detail still refers to this specific posting.
    if title and title.casefold() != str(job.get("title") or "").casefold():
        return job
    desc = trim_job_description(
        plain,
        ("Das können Sie bewegen", "Das erwartet Sie", "Ihre Aufgaben",
         "Your responsibilities", "Your tasks", "What you can move",
         "The following challenges await you", "Your new responsibilities"),
        ("Neugierig? Jetzt bewerben", "Jetzt bewerben!", "ReqID:",
         "Interested? Apply now", "Apply now!", "Your contact", "Related jobs"),
    )
    if len(desc) >= 160 and re.search(
            r"Das bringen Sie mit|Ihr Profil|Your profile|Your qualifications|"
            r"What you bring|Your skills", desc, re.I):
        job["description"] = desc[:18000]
        job["source_mode"] = "html_detail"
    return job
