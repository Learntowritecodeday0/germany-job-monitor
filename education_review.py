#!/usr/bin/env python3
"""Conservative advertised education parsing for a university-qualified candidate.

Only qualification/profile text is examined. 'Possible overqualified' is a
career-preference hint for roles demanding only vocational qualifications; it
is not an employer decision, an eligibility verdict, or a reason to auto-reject.
"""
from __future__ import annotations

import re
from qualification_priority import qualification_section, split_requirements
from monitor import plain_text

BACHELOR = re.compile(r"\b(?:bachelor(?:['’]s)?(?:\s+degree)?|b\.?sc\.?|bachelorabschluss|bachelorstudium|bachelor[- ]abschluss)\b",re.I)
MASTER = re.compile(r"\b(?:master(?:['’]s|s)?(?:\s+degree)?|m\.?sc\.?|masterabschluss|masterstudium|master[- ]abschluss|diplom(?:abschluss)?|diploma\s+(?:degree|in))\b",re.I)
PHD = re.compile(r"\b(?:ph\.?d\.?|doctorate|doctoral\s+degree|doctoral\s+qualification|promotio[n]?|promoviert(?:e[nrsm]?)?|doktorgrad|doktor(?:abschluss)?)\b",re.I)
GENERIC_DEGREE = re.compile(
 r"\b(?:university\s+degree|academic\s+degree|degree\s+in\s+(?:chemistry|physics|materials)|"
 r"(?:completed|relevant|successful|abgeschlossen(?:es|en|e)?)\s+(?:university|college|hochschul|universit[aä]ts)?\s*studium|"
 r"(?:abgeschlossen(?:er|es|en|e)?|wissenschaftlicher)\s+(?:hochschulabschluss|universit[aä]tsabschluss)|"
 r"hochschulabschluss|universit[aä]tsabschluss|studium\s+(?:der|des|im|in|mit)\b|"
 r"(?:completed|relevant)\s+studies\s+in)\b",re.I)
VOCATIONAL = re.compile(
 r"\b(?:berufsausbildung|ausbildung\s+(?:als|zum|zur|in\s+(?:einem|einer)|im\s+bereich)|"
 r"(?:abgeschlossen(?:e|en|er|es)?)\s+(?:technische\s+|kaufm[aä]nnische\s+|einschl[aä]gige\s+)?ausbildung|"
 r"vocational\s+(?:training|qualification|education)|technical\s+training|apprenticeship|"
 r"(?:trained|qualified)\s+(?:lab\s+)?technician|berufsabschluss|\btechnikerabschluss|erfahrener\s+techniker)\b",re.I)
PREFERRED = re.compile(r"\b(?:preferred|desirable|ideally|preferably|a\s+plus|advantage(?:ous)?|"
 r"w[uü]nschenswert|von\s+vorteil|idealerweise|bevorzugt|vorzugsweise|w[uü]rde\s+begr[uü][sß]t)\b",re.I)
MUST = re.compile(r"\b(?:required|mandatory|must\s+have|minimum|at\s+least|essential|"
 r"abgeschlossen(?:e|en|er|es)?|erforderlich|zwingend|vorausgesetzt|mindestens|erfolgreich\s+abgeschlossen)\b",re.I)
UNIVERSITY_WORD = re.compile(r"\b(?:studium|hochschulabschluss|universit[aä]tsabschluss|university\s+degree|"
 r"academic\s+degree|bachelor|master|ph\.?d\.?|promotio[n]?|diplom)\b",re.I)


def _empty(status='not_specified'):
    return {'status':status,'minimum_level':None,'minimum_evidence':None,
            'preferred_level':None,'preferred_evidence':None,
            'alternative_routes':[], 'possible_overqualified':False,
            'note':'Education is not stated in the identifiable qualifications section.'}


def _level_from_segment(text):
    # An accepted 'Master or PhD' is a Master-level minimum, not proof that a
    # PhD is preferred. Likewise 'Bachelor or Master' starts at Bachelor.
    levels=[]
    if BACHELOR.search(text):levels.append(('Bachelor',1))
    if MASTER.search(text):levels.append(('Master / Diplom',2))
    if PHD.search(text):levels.append(('PhD / Promotion',3))
    if GENERIC_DEGREE.search(text):levels.append(('University degree / Studium (level unspecified)',0))
    if levels:
        specific=[x for x in levels if x[1]>0]
        return min(specific,key=lambda x:x[1])[0] if specific else levels[-1][0]
    if VOCATIONAL.search(text):return 'Vocational training / Ausbildung'
    return None



# Profile headings on Personio, Softgarden, SmartRecruiters and custom pages
# frequently lose their colon when converted into plain text. Limit fallback
# extraction to recognizable qualification headings, never general job tasks.
EDUCATION_PROFILE_HEADING = re.compile(
    r"\b(?:das\s+bringst\s+du\s+mit|das\s+bringen\s+sie\s+mit|"
    r"das\s+solltest\s+du\s+mitbringen|was\s+du\s+mitbringst|"
    r"dein\s+profil|ihr\s+profil|your\s+profile|"
    r"your\s+qualifications|your\s+background|what\s+you\s+bring|"
    r"who\s+you\s+are|qualifications|requirements)\b\s*[:\-–]?", re.I)
EDUCATION_PROFILE_FOOTER = re.compile(
    r"\b(?:das\s+(?:bieten|erwartet)\s+(?:wir|dich)|wir\s+bieten|"
    r"was\s+wir\s+bieten|our\s+work\s+culture|"
    r"why\s+(?:us|join\s+us)|what\s+we\s+offer|our\s+benefits|"
    r"equal\s+opportunity)\b\s*[:\-–]?", re.I)


def _education_profile(raw):
    text = plain_text(raw)[:30000]
    heading = EDUCATION_PROFILE_HEADING.search(text)
    if heading:
        section = text[heading.end():]
        footer = EDUCATION_PROFILE_FOOTER.search(section)
        return (section[:footer.start()] if footer else section)[:10000].strip(), True
    return qualification_section(raw)


def parse_clauses(profile):
    clauses=[piece for clause in split_requirements(profile) for piece in re.split(r';\s*(?=(?:M\.?Sc\.?|Master|Ph\.?D\.?|Promotion|Bachelor|Diplom)\b)',clause,flags=re.I)]
    education=[]
    for clause in clauses:
        level=_level_from_segment(clause)
        if not level:continue
        if PREFERRED.search(clause) and not MUST.search(clause):priority='preferred'
        else:priority='minimum_or_listed'
        education.append({'level':level,'text':re.sub(r'\s+',' ',clause)[:220],'priority':priority})
    return education


def education_review(job:dict)->dict:
    raw=str(job.get('description') or '')
    if job.get('source_mode')=='html_fallback' or len(plain_text(raw))<100:
        return _empty('unavailable')
    profile,has=_education_profile(raw)
    if not has or not profile:return _empty('unavailable')
    education=parse_clauses(profile)
    if not education:
        # Keep recognized degree evidence from the legacy section splitter if
        # the newly recognized heading happens to be a false positive.
        legacy_profile, legacy_found = qualification_section(raw)
        if legacy_found and legacy_profile != profile:
            education = parse_clauses(legacy_profile)
    if not education:return _empty()

    required=[e for e in education if e['priority']=='minimum_or_listed']
    preferred=[e for e in education if e['priority']=='preferred']
    # Use first recognized minimum clause, normally strongest evidence of
    # employers' requirement, while avoiding false 'minimum' claims if only
    # softer language is present: the UI uses 'Advertised education'.
    entry=required[0] if required else None
    pref=preferred[0] if preferred else None
    all_text=' '.join(e['text'] for e in education)
    vocational=any(VOCATIONAL.search(e['text']) for e in required)
    university=any(UNIVERSITY_WORD.search(e['text']) for e in education)
    # A degree explicitly accepted as an alternative is not vocational-only.
    possible_overqualified=bool(vocational and not university)
    alternatives=[]
    if entry and VOCATIONAL.search(entry['text']) and UNIVERSITY_WORD.search(entry['text']):
        alternatives.append('University study or vocational/technical qualification accepted')
    if entry and MASTER.search(entry['text']) and PHD.search(entry['text']):
        alternatives.append('Master or PhD accepted; PhD is not automatically preferred')
    if entry and BACHELOR.search(entry['text']) and MASTER.search(entry['text']):
        alternatives.append('Bachelor or Master accepted')
    return {
       'status':'identified',
       'minimum_level':entry['level'] if entry else None,
       'minimum_evidence':entry['text'] if entry else None,
       'preferred_level':pref['level'] if pref else None,
       'preferred_evidence':pref['text'] if pref else None,
       'alternative_routes':alternatives,
       'possible_overqualified':possible_overqualified,
       'note':('Possible overqualified is only a search-priority warning, not a hiring or legal determination.'
               if possible_overqualified else 'Based on advertised education wording; verify the official listing.')
    }
