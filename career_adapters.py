"""Public career-board readers for PCT, CeramTec, and SmartRecruiters.

Only official pages and the documented public postings API. Unreadable pages
raise errors instead of implying that zero jobs are open. Do not scrape gated
content or infer missing job descriptions.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.chunks = []
        self.h1 = []
        self.in_h1 = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','svg','noscript'):
            self.hidden += 1
        if tag == 'h1' and not self.hidden:
            self.in_h1 = True
        if tag in ('p','div','li','h1','h2','h3','h4','br','section','td') and not self.hidden:
            self.chunks.append('\n')

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_h1 = False
        if tag in ('script','style','svg','noscript') and self.hidden:
            self.hidden -= 1
        if tag in ('p','div','li','h1','h2','h3','h4','section','td') and not self.hidden:
            self.chunks.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.chunks.append(data)
            if self.in_h1:
                self.h1.append(data)


def visible(text):
    p = VisibleText()
    p.feed(str(text or ''))
    return p, '\n'.join(x.strip() for x in ''.join(p.chunks).splitlines() if x.strip())


def trim_job_description(text, markers, end_markers):
    lower = text.casefold()
    indices = [lower.find(x.casefold()) for x in markers]
    indices = [x for x in indices if x >= 0]
    if not indices:
        return ''
    start = min(indices)
    lower_tail = lower[start:]
    ends = [lower_tail.find(x.casefold()) for x in end_markers]
    ends = [x for x in ends if x > 140]
    selection = text[start:start + min(ends)] if ends else text[start:]
    return ' '.join(selection.split())[:18000]


def same_host(url, root):
    candidate = urlsplit(url)
    base = urlsplit(root)
    return candidate.scheme == 'https' and candidate.hostname == base.hostname


class PCTLinks(HTMLParser):
    """Extract public job detail links from the employer's careers table."""
    def __init__(self, root):
        super().__init__(convert_charrefs=True)
        self.root = root
        self.row = None
        self.cell = None
        self.anchor = None
        self.rows = []
        self.links = []

    def _link(self, href):
        url = urljoin(self.root, href)
        path = urlsplit(url).path.rstrip('/')
        if (same_host(url, self.root) and
            '/pct-chemie/karriere/offene-stellen/' in path and
            len(path.split('/offene-stellen/', 1)[-1]) >= 6):
            return url
        return ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.row = {'cells': [], 'links': []}
        if tag in ('td', 'th') and self.row is not None:
            self.cell = []
        if tag == 'a':
            link = self._link(attrs.get('href', ''))
            if link:
                self.anchor = {'url': link, 'text': []}

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        if self.anchor is not None:
            self.anchor['text'].append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            self.anchor['text'] = ' '.join(''.join(self.anchor['text']).split())
            self.links.append(self.anchor)
            if self.row is not None:
                self.row['links'].append(self.anchor)
            self.anchor = None
        if tag in ('td', 'th') and self.cell is not None:
            if self.row is not None:
                self.row['cells'].append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse_pct_listing(company, page_html):
    parsed = PCTLinks(company['careers_url'])
    parsed.feed(page_html)
    by_url = {}
    for row in parsed.rows:
        if not row['links']:
            continue
        cells = row['cells']
        title = cells[0] if cells else ''
        location = cells[2] if len(cells) >= 3 else ''
        for link in row['links']:
            by_url[link['url']] = {'title': title or link['text'], 'location': location}
    # Some responsive layouts omit <tr>; full detail pages will provide title.
    for link in parsed.links:
        by_url.setdefault(link['url'], {'title': link['text'] if link['text'].casefold() != 'details' else '', 'location': ''})
    if not by_url:
        raise ValueError('PCT career page exposed no official job links; verify markup')
    return [{
        'key':f"pct_html:{company['slug']}:{urlsplit(url).path.casefold()}",
        'company':company['name'], 'title':data['title'], 'location':data['location'],
        'country':'', 'description':'', 'url':url, 'published_at':None,
        'source_modified_at':None, 'platform':'pct_html',
        'source_mode':'html_fallback',
    } for url,data in by_url.items()]


def enrich_pct_job(job, page_html):
    parsed, text = visible(page_html)
    title = ' '.join(''.join(parsed.h1).split())
    desc = trim_job_description(text, ('Deine Aufgaben','Ihre Aufgaben','Aufgabenschwerpunkte'),
                                ('Deine Benefits','Ihre Benefits','Hier startet Dein Weg',
                                 'zurück zur Übersicht', 'Kontakt'))
    if title and not job.get('title'):
        job['title'] = title
    if not job.get('title'):
        raise ValueError('PCT detail page lacks job title')
    if desc and len(desc) >= 140:
        job['description'] = desc
        job['source_mode'] = 'html_detail'
    # No source date: do not mistake discovery date for publication date.
    return job


class CeramTecLinks(HTMLParser):
    def __init__(self, root):
        super().__init__(convert_charrefs=True)
        self.root = root
        self.anchor = None
        self.items = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        raw = dict(attrs).get('href', '')
        url = urljoin(self.root, raw)
        match = re.fullmatch(r'/Vacancies/(\d+)/Description/(\d+)/?', urlsplit(url).path, re.I)
        if match and same_host(url, self.root):
            self.anchor = {'id':match.group(1), 'url':url, 'text':[]}

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor['text'].append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            self.anchor['title'] = ' '.join(''.join(self.anchor['text']).split())
            if self.anchor['title']:
                self.items.setdefault(self.anchor['id'], self.anchor)
            self.anchor = None


def parse_ceramtec_listing(company, page_html):
    parsed = CeramTecLinks(company['careers_url'])
    parsed.feed(page_html)
    if not parsed.items:
        raise ValueError('CeramTec recent results lacked official vacancy links')
    return [{
        'key':f"ceramtec_recent:{company['slug']}:{x['id']}",
        'company':company['name'], 'title':x['title'], 'location':'', 'country':'',
        'description':'', 'url':x['url'], 'published_at':None,
        'source_modified_at':None, 'platform':'ceramtec_recent',
        'source_mode':'recent_title_only','source_coverage':'recent_window_not_complete',
    } for x in parsed.items.values()]


def enrich_ceramtec_job(job, page_html):
    parsed, text = visible(page_html)
    desc = trim_job_description(text, ('mit folgenden Aufgabenschwerpunkten:', 'Ihr Profil:',
                                       'Ihre Aufgaben:', 'Aufgaben und Verantwortlichkeiten'),
                                ('Wir machen keine Unterschiede', 'Benefits', 'Über uns',
                                 'Kontakt', '© CeramTec'))
    # Detail page may have intro before the task section, but never infer
    # qualifications from the employer navigation or social-media footer.
    if desc and len(desc) >= 140:
        job['description'] = desc
        job['source_mode'] = 'html_detail'
    match = re.search(r'(?im)^Standort:\s*$\s*^([^\n]+)$', text)
    if not match:
        match = re.search(r'(?im)^Standort:\s*([^\n]{2,65})$', text)
    if match:
        site = ' '.join(match.group(1).split())
        if 1 < len(site) < 60 and not any(word in site.casefold() for word in ('bereich:', 'einstieg:', 'art:')):
            job['location'] = site
            job['country'] = 'Germany'  # The country filter still verifies via location rules.
    return job


def normalize_smartrecruiters_listing(company, item):
    ident = str(item.get('id') or '').strip()
    title = str(item.get('name') or '').strip()
    if not ident or not title:
        raise ValueError('SmartRecruiters posting missing ID or title')
    loc = item.get('location') or {}
    if not isinstance(loc, dict):
        loc = {}
    city, region, country = (str(loc.get(k) or '').strip() for k in ('city','region','country'))
    location = ', '.join(x for x in (city,region) if x)
    if country and country.casefold() in ('de', 'deu', 'germany'):
        location = ', '.join(x for x in (location,'Germany') if x)
    elif country:
        location = ', '.join(x for x in (location,country) if x)
    url = str(item.get('postingUrl') or '').strip()
    if not url.startswith('https://jobs.smartrecruiters.com/'):
        url = f"https://jobs.smartrecruiters.com/{company['slug']}/{ident}"
    return {
        'key':f"smartrecruiters:{company['slug']}:{ident}",
        'company':company['name'], 'title':title,
        'location':location, 'country':country, 'description':'',
        'url':url, 'published_at':item.get('releasedDate') or None,
        'source_modified_at':None, 'platform':'smartrecruiters',
        'source_mode':'api_list_only',
    }


def enrich_smartrecruiters_job(job, detail):
    if not isinstance(detail, dict):
        raise ValueError('SmartRecruiters detail is not a JSON object')
    ad = detail.get('jobAd') or {}
    sections = ad.get('sections') or {} if isinstance(ad, dict) else {}
    if not isinstance(sections, dict):
        sections = {}
    values = []
    for key in ('jobDescription','qualifications','additionalInformation'):
        val = sections.get(key) or {}
        if isinstance(val, dict):
            val = val.get('text') or ''
        if isinstance(val, str) and val.strip():
            # Parse HTML only from explicit job-ad sections.
            _, text = visible(val)
            values.append(f'{key}: ' + ' '.join(text.split()))
    if values:
        job['description'] = ' '.join(values)[:18000]
        job['source_mode'] = 'api_detail'
    url = detail.get('postingUrl')
    if isinstance(url, str) and url.startswith('https://jobs.smartrecruiters.com/'):
        job['url'] = url
    job['published_at'] = detail.get('releasedDate') or job.get('published_at')
    return job
