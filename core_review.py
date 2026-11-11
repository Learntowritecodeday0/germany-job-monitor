#!/usr/bin/env python3
"""Core-task vs essential-specialization cues for manual job screening.

Not a hiring-fit score. Work tasks and qualifications are read separately to
avoid promoting a role solely because a few generic methods match.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'data/state.json'
PUBLIC = ROOT / 'docs/jobs.json'

# Positive evidence: hands-on experience actually documented in project record.
# Each category is intentionally narrower than a job family name.
DOCUMENTED_CORE = [
 ('Nanoparticle and sol-gel synthesis', [r'\b(?:silica|sio[₂2]|aerogel|sol[- ]gel|nanopartic\w*|nanopartik\w*|kolloid\w*|colloid\w*)\b']),
 ('Formulation and dispersion experiments', [r'\bformulat(?:ion|ions|e|ing)\b',r'\bformulier\w*\b',r'\bemulsion\w*\b',r'\bdispersions?\b',r'\bsurfactant\w*\b',r'\btensid\w*\b']),
 ('Materials and particle characterization', [r'\b(?:SEM|TEM|FTIR|FT-IR|DLS|TGA|DSC|BET|XRD)\b',r'\bzeta[ -]?(?:potential|potenzial)\b',r'\b(?:materials?|particle|surface) characteri[sz]\w*\b',r'\bmaterialcharakteris\w*\b',r'\belektronenmikroskop\w*\b']),
 ('Surface functionalization and wettability', [r'\bsurface functionaliz\w*\b',r'\boberfl[aä]chenfunktionalis\w*\b',r'\bhydrophob\w*\b',r'\bwetting\b',r'\bbenetz\w*\b',r'\bcontact angle\b']),
 ('Design of experiments and experimental optimization', [r'\bDoE\b',r'\bdesign of experiments\b',r'\bversuchsplan\w*\b',r'\bexperimental design\b']),
 ('Laboratory synthesis scale-up', [r'\bscale[- ]?up\b',r'\bupscal\w*\b',r'\blab[- ]?scale\b',r'\bpilot[- ]?scale\b',r'\bskalier\w*\b']),
]
# These are core fields that cannot be established by nanoparticle R&D alone.
SPECIALIZED_CORE = [
 ('Composite winding or layup', [r'\b(?:filament|composite|fibre|fiber) winding\b',r'\bfaserwickel\w*\b',r'\bwickelprozess\w*\b',r'\bprepreg\b']),
 ('Aircraft structures or certification', [r'\baircraft structures?\b',r'\bairframe\b',r'\bairworthiness\b',r'\b(?:CS[- ]?23|DO[- ]?160|EASA Part)\b',r'\baircraft development programs?\b']),
 ('Semiconductor fabrication', [r'\b(?:ALD|CVD|PVD|PECVD|CMP)\b',r'\blithograph\w*\b',r'\bwafer (?:fabricat\w*|manufactur\w*|process\w*)\b',r'\bepitaxy\b']),
 ('Battery electrochemistry and cells', [r'\belectrochem\w*\b',r'\belektrochem\w*\b',r'\belectrode slurr\w*\b',r'\b(?:battery|lithium[- ]ion) (?:cells?|chemistry)\b',r'\bcathode\b',r'\banode\b']),
 ('Mechanical design and CAD', [r'\b(?:CATIA|SolidWorks|Autocad|Abaqus|ANSYS)\b',r'\b(?:CAD|FEA|CFD)\b',r'\bmechanical design\b',r'\bfinite element\b']),
 ('Scientific instrument or fluidic-system construction', [r'\b(?:build|design|develop)\w* (?:of )?(?:scientific|analytical|measurement) instruments?\b',r'\bfluidic (?:system|design|integration)\b',r'\binstrument (?:architecture|integration|construction)\b']),
 ('Industrial lacquer films and curing', [r'\b(?:lacquer|lackfilm|pigmentierte lacke|paint film)\w*\b',r'\b(?:electron[- ]beam|UV) cur\w*\b',r'\belektronenstrahlh[aä]rt\w*\b']),
 ('Embedded electronics or controls', [r'\b(?:embedded software|PLC|SPS[- ]?programmierung|PCB layout|C\+\+)\b',r'\b(?:hardware[- ]in[- ]the[- ]loop|HiL)\b']),
 ('GMP validation and pharmaceutical production', [r'\bGMP\b',r'\bcleaning validation\b',r'\bpharmaceutical manufacturing validation\b']),
]

# Split the advertising copy into tasks and formal requirements, retaining
# unknowns rather than inferring requirements from the employer's product.
TASK_START = re.compile(r'\b(?:your (?:day[- ]to[- ]day|tasks|responsibilities|mission)|(?:main )?responsibilities|(?:key )?tasks|what you(?: will)? do|deine aufgaben|ihre aufgaben|t[aä]tigkeiten|hauptaufgaben|zust[aä]ndigkeiten)\s*[:\-]', re.I)
REQ_START = re.compile(r'\b(?:your profile|your qualifications|what you bring|what we expect|your requirements|ihr profil|dein profil|anforderungen|das bringen sie mit|qualifikationen)\s*[:\-]', re.I)
FOOTER = re.compile(r'\b(?:why us|why join us|what we offer|benefits|perks|we recognize that|equal opportunity|über uns|was wir bieten|wir bieten|unsere benefits|apply now)\s*[:\-]?', re.I)


def _catalog_match(text: str, catalog) -> list[str]:
    return [title for title, terms in catalog if any(re.search(term,text,re.I) for term in terms)]


def split_role(description: str) -> tuple[str,str,bool]:
    desc = description[:30000]
    foot = FOOTER.search(desc)
    if foot: desc = desc[:foot.start()]
    req = REQ_START.search(desc)
    tasks = desc[:req.start()] if req else desc
    requirements = desc[req.end():] if req else ''
    markers = list(TASK_START.finditer(tasks))
    # Use the last task heading, usually the detailed 'Your day-to-day' after an intro.
    if markers: tasks = tasks[markers[-1].end():]
    return tasks[:14000], requirements[:9000], bool(req)


def core_review(job: dict) -> dict:
    description = str(job.get('description') or '').strip()
    if job.get('hide_by_default') or re.search(r'\b(?:unsolicited application|initiativbewerbung|talent pool|general application)\b', str(job.get('title') or ''), re.I):
        return {'core_review':'Outside preferred job families','core_documented_tasks':[],
                'core_specializations_to_verify':[], 'core_review_basis':'Excluded by selected job-family preferences'}
    if len(description) < 120 or job.get('source_mode') == 'html_fallback':
        return {'core_review':'Insufficient role details','core_documented_tasks':[],
                'core_specializations_to_verify':[], 'core_review_basis':'Tasks or qualifications unavailable'}
    tasks,requirements,has_req=split_role(description)
    # Use the role's main task section for evidence, and qualification section
    # for specialization requirements. Do not turn a generic title into a match.
    direct_tasks = _catalog_match(tasks, DOCUMENTED_CORE)
    gap_tasks = _catalog_match(tasks, SPECIALIZED_CORE)
    gap_requirements = _catalog_match(requirements, SPECIALIZED_CORE)
    gaps = list(dict.fromkeys(gap_requirements + gap_tasks))
    # Only clearly described tasks count as documented central-method overlap.
    if gaps and not direct_tasks:
        label = 'Specialized core work — verify experience'
    elif gaps and direct_tasks:
        label = 'Core-method overlap; specialized gaps'
    elif len(direct_tasks) >= 2:
        label = 'Several core methods overlap'
    elif direct_tasks:
        label = 'Some core-method overlap'
    else:
        label = 'Core technical fit unclear'
    if not tasks.strip():
        label = 'Insufficient role details'
    return {
        'core_review':label,
        'core_documented_tasks':direct_tasks[:4],
        'core_specializations_to_verify':gaps[:4],
        'core_review_basis':'Tasks and listed qualifications; rule-based manual screening' if has_req else 'Role text only; full requirements not separated',
    }


def main() -> int:
    state=json.loads(STATE.read_text(encoding='utf-8'))
    public=json.loads(PUBLIC.read_text(encoding='utf-8'))
    for j in state.get('jobs',{}).values():j.update(core_review(j))
    for j in public.get('jobs',[]):j.update(core_review(j))
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    PUBLIC.write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Added task-and-requirement review to {len(public.get('jobs',[]))} jobs")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
