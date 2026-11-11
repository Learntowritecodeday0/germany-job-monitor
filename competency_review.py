#!/usr/bin/env python3
"""Three-category evidence counts for public job listings.

Counts are recognised topic requirements in a posting, NOT a quantified hiring
fit, eligibility result, probability, or complete list of essential criteria.
Only explicitly documented applicant capabilities receive supported=True.
Unlisted skills remain unknown, not automatically absent in real life.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from core_review import FOOTER
from monitor import plain_text

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'data/state.json'
PUBLIC = ROOT / 'docs/jobs.json'

# Supported flags refer to the documented NTNU / Newcastle / bachelor's record.
# Distinguish scientific subject/technology from techniques (methods).
TECHNICAL = [
    ('Silica / SiO₂ chemistry', True, [r'\bsilica\b',r'\bsio\s*[₂2]\b',r'\bkiesels[aä]ure\b']),
    ('Cellulose materials', True, [r'\bcellulos\w*\b',r'\bcellulose\b',r'\bzellulos\w*\b']),
    ('Alumina synthesis', True, [r'\balumina\b',r'\baluminium oxide\b',r'\baluminiumoxid\b',r'\baluminum oxide\b']),
    ('Nanoparticles / colloidal materials', True, [r'\bnanopartic\w*\b',r'\bnanopartik\w*\b',r'\bcolloid\w*\b',r'\bkolloid\w*\b']),
    ('Silica aerogels / porous materials', True, [r'\baerogel\w*\b',r'\bporous silica\b',r'\bpor[oö]se\w* material\w*\b']),
    ('Sol-gel synthesis', True, [r'\bsol[- ]gel\b']),
    ('Surface functionalization / wettability', True, [r'\bsurface functionaliz\w*\b',r'\boberfl[aä]chenfunktionalis\w*\b',r'\bhydrophob\w*\b',r'\bwetting behavior\b',r'\bbenetzbarkeit\b']),
    ('Surfactant-based emulsions / colloidal formulation', True, [r'\bemulsion\w*\b',r'\bsurfactant\w*\b',r'\btensid\w*\b',r'\bkolloidale formulier\w*\b']),
    ('Graphene and electrospun nylon films', True, [r'\bgraphene\b',r'\bgraphen\b',r'\belectrospinn\w*\b',r'\belektrospinn\w*\b']),
    # Missing *direct* expertise (not asserting these cannot be learned).
    ('Battery-cell electrochemistry', False, [r'\bbatter(?:y|ies)\b',r'\bbatterie\w*\b',r'\belectrode\w*\b',r'\bcathode\w*\b',r'\banode\w*\b',r'\belektrochem\w*\b',r'\belectrochem\w*\b']),
    ('Industrial semiconductor fabrication', False, [r'\b(?:wafer|lithograph\w*|epitax\w*|PECVD|MOCVD|CMP)\b',r'\bhalbleiterfertig\w*\b']),
    ('Composite winding / layup engineering', False, [r'\b(?:filament|composite|fibre|fiber) winding\b',r'\bwickelprozess\w*\b',r'\bprepreg\b',r'\bfaserverbundfertig\w*\b']),
    ('Electric motors / propulsion-system engineering', False, [r'\belectric motors?\b',r'\belektromotor\w*\b',r'\belectric drive systems?\b',r'\bpropulsion system\w*\b']),
    ('Mechanical design / aircraft systems', False, [r'\bmechanical design\b',r'\bairframe\b',r'\baircraft structures?\b',r'\bCAD design\b']),
    ('Scientific instrument hardware development', False, [r'\b(?:build|design|develop)\w* (?:of )?(?:scientific|analytical|measurement) instruments?\b',r'\binstrument (?:architecture|integration|construction)\b',r'\bfluidic systems? design\b']),
    ('Industrial lacquer-film formulation / curing', False, [r'\black(?:film|system|en|e)\w*\b',r'\blacquer\w*\b',r'\belectron[- ]beam cur\w*\b',r'\belektronenstrahlh[aä]rt\w*\b']),
    ('Industrial polymer composite engineering', False, [r'\bcomposite (?:design|manufactur\w*|engineering)\b',r'\bpolymer composite development\b']),
]

METHODS = [
    ('DoE / experimental design', True, [r'\bdoe\b',r'\bdesign of experiments\b',r'\bversuchsplan\w*\b']),
    ('DLS / zeta potential', True, [r'\bdls\b',r'\bdynamic light scattering\b',r'\bzeta[ -]?(?:potential|potenzial)\b']),
    ('SEM / EDS microscopy', True, [r'\bsem\b',r'\bscanning electron microsc\w*\b',r'\b(?:edx|eds)\b',r'\benergy[- ]dispersive x[- ]ray\b']),
    ('TEM', True, [r'\btem\b',r'\btransmission electron microscop\w*\b']),
    ('FTIR', True, [r'\b(?:ftir|ft-ir)\b',r'\bfourier[- ]transform infrared\b']),
    ('TGA / DSC', True, [r'\b(?:tga|dsc)\b',r'\bthermogravimetr\w*\b',r'\bdifferential scanning calorimetr\w*\b']),
    ('BET / pore analysis', True, [r'\bbet\b\s+(?:surface|measurement|analysis|test)',r'\bbjh\b',r'\bpore size analy\w*\b']),
    ('XRD', True, [r'\bxrd\b',r'\bx[- ]ray diffraction\b']),
    ('Contact-angle testing', True, [r'\bcontact[- ]angle\b',r'\bkontaktwinkel\b']),
    ('Filtration / dialysis / rotary evaporation', True, [r'\bfiltrat\w*\b',r'\bdialys\w*\b',r'\brotary evaporat\w*\b',r'\brotationsverdampf\w*\b',r'\beindampf\w*\b']),
    ('Laboratory synthesis scale-up', True, [r'\bscale[- ]?up\b',r'\bupscal\w*\b',r'\bskalier\w*\b']),
    ('Emulsion preparation and process-variable studies', True, [r'\bemulsification\b',r'\bemulsion (?:prepar\w*|formulat\w*|develop\w*)\b',r'\bemulsionsherstell\w*\b']),
    ('UV–Vis spectroscopy', True, [r'\buv[ -]?vis\b',r'\buv visible spectroscopy\b']),
    ('Electrochemical impedance / cyclic voltammetry', False, [r'\beis\b',r'\belectrochemical impedance\b',r'\bcyclic voltammetr\w*\b',r'\bzyklische voltammetr\w*\b']),
    ('HPLC / LC-MS / GC-MS', False, [r'\bhplc\b',r'\blc[- ]?ms\b',r'\bgc[- ]?ms\b']),
    ('Industrial composite winding techniques', False, [r'\bfilament winding\b',r'\b(?:composite|fiber|fibre) winding\b',r'\bwickelverfahren\b']),
    ('CAD / finite-element design', False, [r'\b(?:CAD|FEA|CFD|CATIA|SolidWorks|Abaqus|Simulink)\b']),
    ('Embedded software / Python SDK programming', False, [r'\bSDK\b',r'\bpython (?:programming|coding|development)\b',r'\bembedded (?:software|programming)\b',r'\bC\+\+\b']),
]

GENERAL = [
    ('Cross-team collaboration', True, [r'\bteamwork\b',r'\bteamarbeit\b',r'\bcross[- ]functional\b',r'\bcollaborat\w*\b',r'\bteamf[aä]hig\w*\b']),
    ('Technical documentation / SOPs', True, [r'\b(?:SOP|SOPs)\b',r'\bdocumentation\b',r'\bdokumentation\b',r'\btechnical reports?\b',r'\btechnical writing\b']),
    ('Research project coordination', True, [r'\bproject management\b',r'\bprojektmanagement\b',r'\bmilestone\w*\b',r'\bresource planning\b']),
    ('Scientific communication', True, [r'\bpresentat\w*\b',r'\bpr[aä]sentier\w*\b',r'\bcommunication skill\w*\b',r'\bkommunikation\w*\b']),
    ('Lab safety / chemical hazards', True, [r'\blab(?:oratory)? safety\b',r'\bchemical safety\b',r'\bchemical hazards?\b',r'\barbeitssicherheit\b']),
    ('Formal ISO / GMP / medical-device validation', False, [r'\b(?:GMP|ISO 13485|ISO 9001|AS9100|EN 9100|IATF 16949)\b',r'\b(?:GMP|quality system) validation\b']),
    ('Senior people management', False, [r'\b(?:lead|manage) (?:a |the )?(?:large |multidisciplinary )?teams?\b',r'\bpeople management\b',r'\bmehrj[aä]hrige f[uü]hrung\w*\b']),
    ('Fluent professional German', False, [r'\b(?:fluent|native|business[- ]fluent|C1|C2)\s+(?:in\s+)?German\b',r'\bverhandlungssicher(?:e|es|en)? deutsch\b',r'\bdeutsch(?:kenntnisse)?\s*(?:C1|C2)\b']),
]


def _matched(text: str, catalog: list[tuple[str, bool, list[str]]]) -> dict:
    found = []
    supported = []
    missing = []
    for name, is_documented, patterns in catalog:
        if any(re.search(p, text, re.I) for p in patterns):
            found.append(name)
            (supported if is_documented else missing).append(name)
    return {
        'matched': len(supported), 'total': len(found),
        'supported': supported, 'verify': missing,
    }


PROFILE_HEADING = re.compile(r'\b(?:your profile|your qualifications|what you bring|your requirements|ihr profil|dein profil|anforderungen|qualifikationen)\b\s*:?', re.I)
TASK_HEADING = re.compile(r'\b(?:your (?:mission|tasks|day[- ]to[- ]day|responsibilities)|what you(?: will)? do|deine aufgaben|ihre aufgaben|t[aä]tigkeiten)\b\s*:?', re.I)


def _role_sections(raw: str) -> tuple[str, str, bool]:
    # Some provider APIs return HTML headings with no trailing colon. Do not
    # require punctuation for 'Your Profile' / 'Your Mission' to be detected.
    text = plain_text(raw)[:30000]
    footer = FOOTER.search(text)
    if footer:
        text = text[:footer.start()]
    profile = PROFILE_HEADING.search(text)
    task_text = text[:profile.start()] if profile else text
    req_text = text[profile.end():] if profile else ''
    task_headings = list(TASK_HEADING.finditer(task_text))
    if task_headings:
        task_text = task_text[task_headings[-1].end():]
    return task_text[:14000], req_text[:9000], bool(profile)


def competency_review(job: dict) -> dict:
    description = str(job.get('description') or '').strip()
    if len(description) < 120 or job.get('source_mode') == 'html_fallback':
        return {'competency_counts': None, 'competency_note': 'Incomplete job description: counts unavailable'}
    tasks, requirements, has_req = _role_sections(description)
    role = ' '.join((str(job.get('title') or ''), tasks, requirements))
    # General attributes must be requested, rather than inferred from a company's
    # boilerplate or from collaboration phrases scattered through main tasks.
    general_text = requirements if has_req else ''
    result = {
        'technical': _matched(role, TECHNICAL),
        'method': _matched(role, METHODS),
        'general': _matched(general_text, GENERAL),
    }
    return {
        'competency_counts': result,
        'competency_note': ('Recognised items in main tasks and requirements, not all essential qualifications; '
                            'supported items reflect documented experience only. No overall fit score.'),
    }


def main() -> int:
    state = json.loads(STATE.read_text(encoding='utf-8'))
    public = json.loads(PUBLIC.read_text(encoding='utf-8'))
    for job in state.get('jobs', {}).values():
        job.update(competency_review(job))
    for job in public.get('jobs', []):
        job.update(competency_review(job))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Added three-category evidence counts to {len(public.get("jobs", []))} jobs')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
