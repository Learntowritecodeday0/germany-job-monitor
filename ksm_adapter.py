"""Public KSM Castings vacancy listing adapter.

Only links to officially published /stellenanzeige/ detail pages are accepted.
The company has engineering opportunities but mostly industrial foundry and
machining positions. A match to materials science is NOT assumed.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from career_adapters import visible, trim_job_description


class KSMJobLinks(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.host = urlsplit(base).hostname
        self.anchor = None
        self.links = {}

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        url = urljoin(self.base, dict(attrs).get("href", ""))
        parts = urlsplit(url)
        if (parts.scheme == "https" and parts.hostname == self.host and
                re.fullmatch(r"/stellenanzeige/[a-z0-9-]+/?", parts.path, re.I)):
            self.anchor = {"url": parts._replace(query="", fragment="").geturl(),
                           "title_parts": []}

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor["title_parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            candidate = self.anchor
            title = " ".join("".join(candidate["title_parts"]).split())
            if len(title) >= 8 and title.casefold() not in (
                    "details", "mehr erfahren", "jetzt bewerben", "weiterlesen"):
                self.links.setdefault(candidate["url"], title)
            self.anchor = None


def parse_ksm_listing(company, page_html):
    parser = KSMJobLinks(company["careers_url"])
    parser.feed(page_html)
    if not parser.links:
        # Do not mark all prior jobs closed on changed markup or access errors.
        raise ValueError("KSM official vacancy page contains no recognized job detail links")
    return [
        {"key": f"ksm_html:{company['slug']}:{urlsplit(url).path.casefold()}",
         "company": company["name"], "title": title,
         "location": "", "country": "", "description": "",
         "url": url, "published_at": None, "source_modified_at": None,
         "platform": "ksm_html", "source_mode": "html_fallback"}
        for url, title in parser.links.items()
    ]


def enrich_ksm_job(job, detail_html):
    parsed, text = visible(detail_html)
    heading = " ".join("".join(parsed.h1).split())
    if heading and heading.casefold() != str(job["title"]).casefold():
        return job
    # Only accept explicit worksite text. The official board contains
    # international operations; company headquarters is never an alternative.
    location = re.search(r"(?im)^Standort\s*:?\s*([^\n]{3,65})$", text)
    if location:
        place = " ".join(location.group(1).split())
        if place.casefold() in ("bergisches land", "hildesheim", "wernigerode",
                               "wuppertal", "bergisch gladbach"):
            job["location"] = place
            job["country"] = "Germany"
    desc = trim_job_description(text,
            ("Das gehört zu Ihren Aufgaben", "Das sind Ihre Aufgaben",
             "Ihre Aufgaben", "Das bringen Sie mit"),
            ("Ihre Benefits", "Kontakt", "Interessiert?", "Ihre Bewerbung"))
    if len(desc) >= 150:
        job["description"] = desc
        job["source_mode"] = "html_detail"
    return job
