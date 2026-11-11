#!/usr/bin/env python3
"""Conservative evidence-led technical review for public job postings.

This is NOT a hiring recommendation or immigration assessment. The overlap
areas reflect methods documented in the project experience record; the system
makes no claim of direct industrial experience or employer eligibility.
No personal identity, nationality, residence permit or CV data is published.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'data' / 'state.json'
PUBLIC = ROOT / 'docs' / 'jobs.json'

# Use reasonably specific scientific terms, not 'materials', 'engineering',
# 'research' or 'process' alone. Tags indicate technique-level overlap ONLY.
DOCUMENTED_METHODS = [
    ('Silica / sol-gel materials', [r'\bsilica\b', r'\bsio\s*[₂2]\b', r'\baerogels?\b', r'\bsol[ -]gel\b', r'\bkiesels[aä]ure\b']),
    ('Nanoparticles / colloids', [r'\bnanopartic\w*\b', r'\bnanopartik\w*\b', r'\bcolloid\w*\b', r'\bkolloid\w*\b', r'\bpartikelgr[oö][ßs]e\b']),
    ('Formulation / dispersion work', [r'\bformulat\w*\b', r'\bformulier\w*\b', r'\bdispers(?:ions?\w*|ing|ed|e|es|ieren|iert\w*)\b', r'\bemulsion\w*\b', r'\bsuspension\w*\b', r'\bstabilizer\b', r'\bstabilisator\w*\b', r'\bsurfactant\w*\b', r'\btensid\w*\b']),
    ('Materials characterization', [r'\b(?:dls|ftir|ft-ir|tga|dsc|tem|sem|bet)\b', r'\bzeta[ -]?(?:potential|potenzial)\b', r'\belektronenmikroskop\w*\b', r'\belectron microscopy\b', r'\bcontact[ -]angle\b', r'\bkontaktwinkel\b', r'\bparticle characterization\b', r'\bmaterialcharakteris\w*\b']),
    ('Surface chemistry', [r'\bsurface functionaliz\w*\b', r'\boberfl[aä]chenfunktionalis\w*\b', r'\bsurface modification\b', r'\bsurface chemistry\b', r'\boberfl[aä]chenchemie\b', r'\bhydrophob\w*\b', r'\bwetting\b', r'\bbenetz\w*\b']),
    ('DoE / experimental design', [r'\bdesign of experiments\b', r'\bdoe\b', r'\bversuchsplan\w*\b', r'\bstatistical experimental design\b']),
    ('Laboratory scale-up', [r'\bscale[ -]?up\b', r'\bupscal\w*\b', r'\bskalier\w*\b', r'\blab[ -]?scale\b', r'\bpilot[ -]scale\b']),
]

ADJACENT_FIELDS = [
    ('Industrial process engineering', [r'\bprocess (?:develop|optim|engineer)\w*\b', r'\bprozess(?:entwick|optim|ingenieur)\w*\b', r'\bmanufacturing process\b']),
    ('Polymer / composite applications', [r'\bpolymer\w*\b', r'\bcomposites?\b', r'\bverbundwerkstoff\w*\b', r'\bharz\w*\b']),
    ('Industrial film coatings', [r'\blacquer\w*\b', r'\black(?:systeme?|e|en)?\b', r'\bcoating film\b', r'\bfilm formation\b', r'\bbeschichtungsfilm\w*\b']),
    ('Scientific instrument applications', [r'\bapplication scientist\b', r'\bapplikationswissenschaftler\b', r'\bfield application\b', r'\binstrument application\b']),
]

# These indicate domain expertise that is not established by the documented
# experiments. They are NOT automatic rejections, and may be preferred only.
DOMAIN_GAPS = [
    ('Aircraft development / aerospace certification', [r'\baircraft development programs?\b', r'\baircraft certification\b', r'\b(?:cs[- ]?23|do[- ]?160|easa part)\b', r'\baerospace materials and processes\b', r'\bluftfahrtzulassung\b']),
    ('Semiconductor fabrication processes', [r'\b(?:ald|cvd|pvd|cmp|pecvd)\b', r'\bwafer (?:fab|process|inspection|manufactur|polish)\w*\b', r'\blithograph\w*\b', r'\bepitax\w*\b', r'\bplating process\b', r'\b(?:2d|two-dimensional) (?:material )?growth\b', r'\bgraphene (?:growth|transfer|processing)\b']),
    ('Battery electrochemistry', [r'\belectrochem\w*\b', r'\belektrochem\w*\b', r'\belectrode (?:slurr\w*|fabricat\w*|manufactur\w*)\b', r'\blithium[ -]ion (?:cell|batter)\w*\b']),
    ('Composite winding / layup processes', [r'\bcomposite winding\b', r'\bfilament winding\b', r'\bfiber winding\b', r'\bfibre winding\b', r'\bprepreg layup\b', r'\bfaserwickel\w*\b', r'\bwickelprozess\w*\b']),
    ('Mechanical design / CAE / CAD', [r'\b(?:solidworks|catia|abaqus|ansys|autocad|inventor)\b', r'\bfinite[ -]element analysis\b', r'\b(?:fea|cfd)\b', r'\bmechanical design engineer\b']),
    ('Scientific instrument construction / fluidics', [r'\b(?:build|design|develop)\w* (?:of )?(?:scientific|analytical|measurement) instruments?\b', r'\bcomplex fluidic systems?\b', r'\bfluidic (?:systems?|design|integration)\b']),
    ('Industrial lacquer curing / film testing', [r'\belectron[ -]beam cur\w*\b', r'\belektronenstrahlh[aä]rt\w*\b', r'\buv cur\w*\b', r'\bpaint film adhesion\b', r'\blackhaftung\b']),
    ('GMP or regulated pharmaceutical production', [r'\bgmp\b', r'\bpharmaceutical manufacturing validation\b', r'\bcleaning validation\b']),
    ('Medical-device risk / regulatory engineering', [r'\biso ?14971\b', r'\bmedical device risk management\b', r'\bdesign control\b']),
    ('Fusion fuel / isotope chemistry', [r'\btritium\b', r'\bisotope exchange\b', r'\bhydrogen isotopes?\b', r'\bfusion fuel\b']),
    ('Optics / laser system engineering', [r'\blaser (?:design|engineering|development)\b', r'\boptical system design\b', r'\bphotonics engineering\b']),
]

PROFILE_HEAD = re.compile(
    r'\b(?:your profile|your qualifications|'
    r'what you bring|what we expect|ihr profil|dein profil|'
    r'anforderungen|das bringen sie mit|das bringst du mit)\s*[:\-]?|'
    r'(?:requirements|qualifications)\s*[:\-]', re.I,
)
PROFILE_END = re.compile(
    r'\b(?:why us|why join us|what we offer|benefits|perks|über uns|'
    r'was wir bieten|we recognize that|equal opportunit(?:y|ies)|'
    r'join our team|apply now|jetzt bewerben)\b', re.I,
)
TECH_TITLE = re.compile(
    r'\b(?:chem\w*|material\w*|werkstoff\w*|formulat\w*|formulier\w*|'
    r'particle\w*|partikel\w*|analyt\w*|scientist|technician|techniker|'
    r'process\w*|prozess\w*|research\w*|entwicklung\w*|entwickler|'
    r'lab(?:or)?\w*|instrument\w*|physic\w*|pharma\w*|developer|engineer|technolog\w*|surface\w*|'
    r'oberfl[aä]chen\w*)\b', re.I,
)

# No headquarters inferred as an applicant's worksite. These are preferences,
# not exclusion rules, and unknown/multi-location postings stay uncertain.
MUNICH_REGION = [
    'munich', 'münchen', 'garching', 'planegg', 'martinsried', 'neuried',
    'gräfelfing', 'haar', 'oberschleißheim', 'unterschleißheim',
    'puchheim', 'germering', 'freising', 'maisach', 'karlsfeld',
    'taufkirchen', 'oberpfaffenhofen', 'weßling', 'wessling', 'starnberg',
]
SOUTH_REGION = [
    'bavaria', 'bayern', 'baden-württemberg', 'baden wuerttemberg',
    'alzenau', 'geretsried', 'penzberg', 'würzburg', 'erlangen', 'nürnberg',
    'regensburg', 'augsburg', 'burghausen', 'wasserburg', 'ingolstadt',
    'stuttgart', 'ulm', 'karlsruhe', 'heidelberg', 'freiburg', 'tübingen',
    'esslingen', 'heilbronn', 'schweinfurt', 'kaufbeuren', 'memmingen',
    'kronberg', 'darmstadt', 'frankfurt', 'hanau',
]


def _match(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _distinct_groups(text: str, catalog) -> list[str]:
    return [name for name, patterns in catalog if _match(text, patterns)]


def _requirements_section(description: str) -> str:
    m = PROFILE_HEAD.search(description)
    if not m:
        return ''
    tail = description[m.end():]
    end = PROFILE_END.search(tail)
    return (tail[:end.start()] if end else tail)[:7000]


def _specialized_years(text: str) -> bool:
    # Require the years and specific prior sector experience to occur nearby.
    sector = r'(?:aircraft|aerospace|aviation|semiconductor|wafer|medical.device|industrial mechanical|luftfahrt|halbleiter)'
    years = r'(?:[5-9]|1\d)\s*(?:\+|[-–]\s*(?:[6-9]|1\d))?\s*(?:years?|jahre[n]?)'
    return bool(re.search(years + r'.{0,110}' + sector, text, re.I) or
                re.search(sector + r'.{0,110}' + years, text, re.I))


def worksite_preference(job: dict) -> str:
    status = job.get('location_status')
    loc = str(job.get('location') or '').casefold()
    if status == 'outside':
        return 'Outside Germany — verify'
    if status != 'germany' or not loc:
        return 'Worksite unverified'
    # Location strings with multiple countries are already flagged upstream.
    if any(x in loc for x in MUNICH_REGION):
        return 'Munich region'
    if any(x in loc for x in SOUTH_REGION):
        return 'Southern Germany'
    if loc.strip() in ('germany', 'deutschland', 'de') or (
        any(x in loc for x in ('remote', 'home office', 'nationwide', 'multiple sites', 'across germany'))
        and not any(x in loc for x in ('berlin','hamburg','zwickau','dresden','leipzig','hannover','köln'))
    ):
        return 'Germany — city unverified'
    return 'Elsewhere Germany'


def review_job(job: dict) -> dict:
    title = str(job.get('title') or '')
    description = str(job.get('description') or '')
    source_limited = (not description.strip() or job.get('source_mode') == 'html_fallback'
                      or len(description.strip()) < 120)
    worksite = worksite_preference(job)
    if job.get('hide_by_default'):
        return {'technical_review': 'Outside preferred job families',
                'method_overlap': [], 'adjacent_overlap': [], 'technical_gaps_to_verify': [],
                'worksite_preference': worksite, 'technical_review_basis': 'Title-based preference exclusion'}
    if source_limited:
        return {'technical_review': 'Insufficient job details',
                'method_overlap': [], 'adjacent_overlap': [], 'technical_gaps_to_verify': [],
                'worksite_preference': worksite, 'technical_review_basis': 'Full description unavailable'}

    # Limit evidence detection to the technical job context (up to footer),
    # rather than boilerplate about the employer, its social events or benefits.
    end = PROFILE_END.search(description)
    role_text = (description[:end.start()] if end else description)[:16000]
    relevant_title = bool(TECH_TITLE.search(title))
    direct = _distinct_groups(f'{title} {role_text}', DOCUMENTED_METHODS) if relevant_title else []
    adjacent = _distinct_groups(f'{title} {role_text}', ADJACENT_FIELDS) if relevant_title else []

    requirements = _requirements_section(description)
    required_or_role = requirements or (title + ' ' + role_text[:3000])
    gaps = _distinct_groups(f'{title} {required_or_role}', DOMAIN_GAPS)
    if _specialized_years(required_or_role):
        gaps.append('Sector-specific years of experience')
    # A generic job description may mention multiple methods. Keep a concise,
    # inspectable sample, not an automatic hiring score.
    direct = direct[:5]
    adjacent = [x for x in adjacent if x not in direct][:3]
    gaps = list(dict.fromkeys(gaps))[:4]

    if not relevant_title or (not direct and not adjacent):
        level = 'Limited documented overlap'
    elif len(direct) >= 2:
        level = 'Multiple method overlaps — verify gaps' if gaps else 'Multiple method overlaps'
    elif direct:
        level = 'Some method overlap — verify gaps' if gaps else 'Some method overlap'
    else:
        level = 'Adjacent scientific principles only'

    return {'technical_review': level, 'method_overlap': direct,
            'adjacent_overlap': adjacent, 'technical_gaps_to_verify': gaps,
            'worksite_preference': worksite,
            'technical_review_basis': 'Job title and public description; rule-based, unverified'}


def review_state(state: dict) -> dict:
    for job in state.get('jobs', {}).values():
        job.update(review_job(job))
    return state


def main() -> int:
    state = json.loads(STATE.read_text(encoding='utf-8'))
    public = json.loads(PUBLIC.read_text(encoding='utf-8'))
    review_state(state)
    for job in public.get('jobs', []):
        job.update(review_job(job))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Added evidence-led technical cues to {len(public.get('jobs', []))} public vacancies")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
