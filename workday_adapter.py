"""Read public Workday career postings from a verified official employer board.

The endpoint is the same public JSON used by the careers page. No login,
authentication bypass, private Workday/HCM APIs, or personal data is involved.
A bounded listing is deliberately treated as partial: a missing job is not
evidence that it has closed.
"""
from __future__ import annotations

import re
from urllib.parse import quote, urlsplit

from career_adapters import visible


def workday_paths(company):
    url = urlsplit(str(company.get("careers_url") or ""))
    host = (url.hostname or "").lower()
    if (url.scheme != "https" or url.port is not None or
            not re.fullmatch(r"[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com", host)):
        raise ValueError("Workday careers URL must use a public HTTPS Workday job host")
    tenant = host.split(".", 1)[0]
    parts = [segment for segment in url.path.split("/") if segment]
    if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
        parts.pop(0)
    if len(parts) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", parts[0]):
        raise ValueError("Workday careers URL must identify one official site")
    site = parts[0]  # Workday site names are case-sensitive.
    expected_host = company.get("workday_host")
    if expected_host and host != expected_host:
        raise ValueError("Workday host does not match verified employer configuration")
    endpoint = f"https://{host}/wday/cxs/{quote(tenant, safe='')}/{quote(site, safe='')}"
    public = f"https://{host}/en-US/{quote(site, safe='')}"
    return endpoint, public


def workday_detail_priority(job):
    """Choose useful public job details before nontechnical or student adverts.

    This is a retrieval priority, not a job-fit rating. It is applied only to
    bounded public job detail lookups, retaining all listings in the feed.
    """
    title = str(job.get("title") or "")
    location = str(job.get("location") or "")
    if re.search(r"ausbildung|praktik|abschlussarbeit|studium|stipendium|sch[nv]upper|"
                 r"werkstudent|internship|trainee|sales|vertrieb|assistant|assistenz|"
                 r"buchhalt|logistik|elektrotechnik|mechatronik|software|informatik|"
                 r"er[p]? consultant|empfang|reinigung|versand|kaufmann|produktionsmitarbeiter",
                 title, re.I):
        return 0
    if re.search(r"\b(?:chem|material|werkstoff|klebstoff|adhesive|adhesiv|"
                 r"rheolog|labor|analyt|formul|research|forsch|r&d)\w*", title, re.I):
        return 5
    if re.search(r"(?:application development|anwendungsentwickl|prozessingenieur|"
                 r"process engineer|produktionsingenieur|process development|"
                 r"physicist|physiker|product development)", title, re.I):
        return 4
    return 0


def normalize_workday_job(company, item):
    if not isinstance(item, dict):
        raise ValueError("Workday posting must be a JSON object")
    raw_path = str(item.get("externalPath") or "")
    path = urlsplit(raw_path)
    if (path.scheme or path.netloc or path.query or path.fragment or
            not re.fullmatch(r"/job/[A-Za-z0-9_./%-]{5,800}", path.path) or
            ".." in path.path or "%2f" in path.path.lower()):
        raise ValueError("Workday posting has an unsafe or malformed job path")
    title = " ".join(str(item.get("title") or "").split())
    if not title:
        raise ValueError("Workday posting missing title")
    _, public = workday_paths(company)
    loc = " ".join(str(item.get("locationsText") or "").split())
    return {
        "key": f"workday_limited:{company['slug']}:{path.path}",
        "company": company["name"],
        "title": title,
        "location": loc,
        "country": "",  # A company HQ is NOT the job's worksite.
        "description": "",
        "url": public + path.path,
        "published_at": None,  # postedOn is relative, not a publication date.
        "source_modified_at": None,
        "platform": "workday_limited",
        "source_mode": "api_list_only",
        "source_coverage": "recent_window_not_complete",
        "_workday_path": path.path,
    }


def enrich_workday_job(job, payload):
    info = payload.get("jobPostingInfo") if isinstance(payload, dict) else None
    if not isinstance(info, dict):
        raise ValueError("Workday detail missing jobPostingInfo")
    # Never attach another posting's qualifications to this job.
    title = " ".join(str(info.get("title") or "").split())
    if title and title.casefold() != job["title"].casefold():
        return job
    raw = str(info.get("jobDescription") or "")
    if raw:
        _, description = visible(raw)
        description = " ".join(description.split())
        if len(description) >= 100:
            job["description"] = description[:18000]
            job["source_mode"] = "api_detail"
    # The list's explicit location is preserved; a detail page should not
    # replace a specific worksite with the employer's generic headquarters.
    return job
