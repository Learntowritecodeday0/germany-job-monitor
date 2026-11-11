#!/usr/bin/env python3
"""Conservative qualification-priority cues from advertised job requirements.

Separates explicit mandatory wording, stated preferences, explicit options to
learn, and neutral listed qualifications. Does not infer eligibility, invent
missing experience, or alter job ranking / notification selection.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from competency_review import TECHNICAL, METHODS, GENERAL, _role_sections
from monitor import plain_text

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'data/state.json'
PUBLIC = ROOT / 'docs/jobs.json'

# Analyse only the qualification/profile section; job tasks and boilerplate are
# not treated as automatic employment requirements.
PROFILE_FALLBACK = re.compile(
    r'(?:\b(?:minimum qualifications|preferred qualifications|job requirements|'
    r'requirements|qualifications|was du mitbringst|das bringst du mit)\s*:'
    r'|\b(?:was sie mitbringen(?: sollten)?|das bringen sie mit|'
    r'qualification and educational requirements|what you need to succeed)\b\s*:?)', re.I)
FOOTER = re.compile(
    r'\b(?:our work culture|why us|why join us|what we offer|benefits|'
    r'perks|our benefits|we recognize that|equal opportunity|'
    r'wir bieten|was wir bieten|deine benefits|unser angebot)\s*[:.]?', re.I)

MANDATORY = re.compile(
    r'\b(?:must\s+(?:have|be|demonstrate)|mandatory|required|essential|'
    r'minimum(?:\s+of)?|at\s+least|prerequisite|non[- ]negotiable|'
    r'zwingend|erforderlich|vorausgesetzt|unbedingt|mindestens|pflicht)\b', re.I)
PREFERRED = re.compile(
    r'\b(?:preferred|preferable|desirable|advantage(?:ous)?|a\s+plus|'
    r'nice[- ]to[- ]have|bonus|w[uü]nschenswert|von\s+vorteil|'
    r'bevorzugt|vorzugsweise)\b', re.I)
IDEALLY = re.compile(r'\b(?:ideally|ideal(?:erweise)?|idealerweise)\b', re.I)
LEARNABLE = re.compile(
    r'\b(?:or\s+(?:the\s+)?(?:willingness|openness|motivation|curiosity)(?:\s+and\s+(?:willingness|openness|motivation|curiosity))?\s+to\s+learn|'
    r'willing(?:ness)?\s+to\s+learn|open\s+to\s+learn|'
    r'can\s+be\s+(?:learned|trained)|'
    r'oder\s+bereitschaft\s+(?:zum\s+)?(?:lernen|erlernen))\b', re.I)
YEAR_REQUIREMENT = re.compile(
    r'\b(?:minimum(?:\s+of)?|at\s+least|mindestens)\s+'
    r'\d+(?:\s*[-–]\s*\d+)?\+?\s*(?:years?|jahre[n]?)\b', re.I)

CATALOGS = (('Technical', TECHNICAL), ('Methods', METHODS), ('General', GENERAL))


def qualification_section(raw: str) -> tuple[str, bool]:
    desc = plain_text(raw)[:30000]
    _, profile, has_profile = _role_sections(desc)
    if not has_profile:
        match = PROFILE_FALLBACK.search(desc)
        if not match:
            return '', False
        profile = desc[match.end():]
    cutoff = FOOTER.search(profile)
    if cutoff:
        profile = profile[:cutoff.start()]
    return profile[:10000].strip(), True


def split_requirements(profile: str) -> list[str]:
    # Personio/Ashby often preserve each bullet as ' - '. Greenhouse may
    # flatten bullets into sentences; split at sentence boundaries as fallback.
    profile = re.sub(r'\s+[-–]\s+(?=[A-ZÄÖÜ][a-zA-ZäöüÄÖÜ])', ' |BULLET| ', profile)
    # Some boards flatten a missing punctuation separator like
    # 'preferable Analytical mindset: ...' into one long sentence.
    profile = re.sub(r'\b(preferable|preferred|desirable)\s+(?=[A-ZÄÖÜ])',
                     r'\1. ', profile)
    parts = []
    for block in profile.split('|BULLET|'):
        parts.extend(re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', block))
    return [part.strip(' .;:\t\n-') for part in parts if len(part.strip()) >= 4]


def _context_status(segment: str, match_start: int) -> str:
    if MANDATORY.search(segment):
        return 'explicit'
    # The employer explicitly accepts learning after joining: not mandatory
    # to already possess the skill at the time of application.
    if LEARNABLE.search(segment):
        return 'learnable'
    if PREFERRED.search(segment):
        return 'preferred'
    # 'Ideally' can qualify a *different* item in the same sentence:
    # 'Experience with DoE, ideally Bayesian optimization'. In that case,
    # DoE is a listed qualification, not itself an optional skill.
    ideal = IDEALLY.search(segment)
    if ideal and ideal.start() <= match_start and match_start - ideal.end() < 65:
        return 'preferred'
    return 'listed'


def _display_name(name: str, clause: str) -> str:
    # Do not turn a preferred battery-industry background into a statement
    # demanding battery-cell electrochemistry where only the sector is named.
    if name == 'Battery-cell electrochemistry' and not re.search(
        r'\b(?:electrochem\w*|elektrochem\w*|battery[- ]cells?|'
        r'batteriezell\w*|electrode\w*|cathode\w*|anode\w*)\b', clause, re.I
    ):
        return 'Battery-sector experience'
    return name


def priority_review(job: dict) -> dict:
    # Import here to keep education parsing separate from the existing
    # requirements catalog without a module import cycle.
    from education_review import education_review
    degree = education_review(job)
    raw = str(job.get('description') or '')
    profile, has_profile = qualification_section(raw)
    if job.get('source_mode') == 'html_fallback' or len(plain_text(raw)) < 120 or not has_profile or not profile:
        return {'education_review': degree, 'qualification_priority': {
            'status': 'unavailable', 'explicit': [], 'preferred': [],
            'learnable': [], 'listed': [], 'experience_flags': [],
            'note': 'A full identifiable qualifications section is unavailable.'
        }}
    items = split_requirements(profile)
    found: dict[str, dict] = {}
    precedence = {'listed': 0, 'preferred': 1, 'learnable': 2, 'explicit': 3}
    for segment in items:
        for category, catalog in CATALOGS:
            for name, documented, patterns in catalog:
                match = next((m for patt in patterns if (m := re.search(patt, segment, re.I))), None)
                if match is None:
                    continue
                # A job may offer training in electrochemical TESTING, without
                # offering training in the entire battery-cell specialization.
                # Do not overstate what the learnability clause covers.
                if (name == 'Battery-cell electrochemistry'
                        and re.search(r'\belectrochem\w* (?:test\w*|characteriz\w*|evaluat\w*)\b', segment, re.I)
                        and not re.search(r'\b(?:battery[- ]cells?|batteriezell\w*|cathode\w*|anode\w*)\b', segment, re.I)):
                    continue
                name_display = _display_name(name, segment)
                status = _context_status(segment, match.start())
                entry = {'name': name_display, 'category': category,
                         'documented': documented}
                previous = found.get(name_display)
                if previous is None or precedence[status] > precedence[previous[0]]:
                    found[name_display] = (status, entry)

    bucket = {'explicit': [], 'preferred': [], 'learnable': [], 'listed': []}
    for status, entry in found.values():
        bucket[status].append(entry)
    for values in bucket.values():
        values.sort(key=lambda entry: (entry['category'], entry['name']))

    experience_flags = []
    for segment in items:
        match = YEAR_REQUIREMENT.search(segment)
        if match:
            summary = re.sub(r'\s+', ' ', segment).strip()
            experience_flags.append({'kind': 'explicit minimum', 'text': summary[:195],
                                     'verification': 'Check relevant industry and years of experience'})
    return {'education_review': degree, 'qualification_priority': {
        'status': 'parsed', **bucket, 'experience_flags': experience_flags[:5],
        'note': ('Only explicit priority wording is used. Other qualifications are listed with '
                 'priority unclear; absence of documented experience is not a legal or hiring decision.')
    }}


def main() -> int:
    state = json.loads(STATE.read_text(encoding='utf-8'))
    public = json.loads(PUBLIC.read_text(encoding='utf-8'))
    for record in state.get('jobs', {}).values():
        record.update(priority_review(record))
    for record in public.get('jobs', []):
        record.update(priority_review(record))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Added qualification priority cues to {len(public.get("jobs", []))} vacancies')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
