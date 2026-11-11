#!/usr/bin/env python3
"""Conservative public-job screening notes. This is NOT a personal eligibility decision.

Runs after monitor.py, before notify.py. The public JSON never contains
applicant nationality, residence-permit details or personal application data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "state.json"
PUBLIC = ROOT / "docs" / "jobs.json"

# Restrictive must-have formulations only. Mere mentions of NATO, EU, export
# controls, citizenship, internationality or equal-opportunity policies do NOT
# establish a disqualifying nationality requirement.
CITIZENSHIP_REQUIREMENT = [
    r"\b(?:must|need|needs|required|mandatory|only|exclusively)\b.{0,70}\b(?:eu|eea|european union|nato(?:[- ]member)?|german|deutsche[rsn]?|us)\b.{0,40}\b(?:citizenship|citizen|nationality|national|passport|staatsangeh[oö]rigkeit)\b",
    r"\b(?:citizenship|citizen|nationality|national|passport|staatsangeh[oö]rigkeit)\b.{0,45}\b(?:eu|eea|european union|nato(?:[- ]member)?|german|deutsche[rsn]?|us)\b.{0,65}\b(?:required|mandatory|only|exclusively|must|need|erforderlich|voraussetzung)\b",
    r"\b(?:only|exclusively)\s+(?:eu|eea|nato|german|us)\s+(?:nationals?|citizens?|passport holders?)\b",
    r"\b(?:eu|eea|nato|german|deutsche[rsn]?)\s+(?:citizenship|nationality|staatsangeh[oö]rigkeit)\s+(?:is\s+)?(?:required|mandatory|essential|erforderlich|voraussetzung)\b",
    r"\b(?:staatsangeh[oö]rigkeit|staatsb[uü]rgerschaft)\b.{0,30}\b(?:deutsch(?:en|e|er)?|eu|nato)\b.{0,40}\b(?:erforderlich|vorausgesetzt|notwendig)\b",
    r"\b(?:only|must be|required to be)\b.{0,45}\b(?:citizens?|nationals?|passport holders?)\s+(?:of|from)\s+(?:an?\s+)?(?:eu|eea|nato|epo|epc|germany|german|us|united states)\b",
    r"\b(?:citizenship|nationality|nationals?|citizens?)\b.{0,75}\b(?:european patent organisation|european patent organization|epc contracting states?|epo member states?)\b.{0,75}\b(?:required|mandatory|only|eligible|must|need)\b",
    r"\b(?:us[- ]person status)\b.{0,35}\b(?:required|mandatory|must|essential)\b",
    r"\b(?:must|required)\b.{0,40}\b(?:us[- ]person status)\b",
]

EXPORT_CONTROL = [
    r"\bitar\b", r"\bear\s*(?:regulations?|controlled|compliance)\b",
    r"\bexport[- ]control(?:led)?\b", r"\bexportkontroll\w*\b",
    r"\bdual[- ]use\s+(?:export|restrictions?|technology|regulations?|control)\b",
]
SECURITY_CLEARANCE = [
    r"\bsecurity clearance\b", r"\b(?:must|requires?|mandatory)\b.{0,50}\b(?:clearance|sicherheits[uü]berpr[uü]fung)\b",
    r"\bsicherheits[uü]berpr[uü]fung\b", r"\b(?:s[uü]\s*[123])\s+(?:clearance|security|sicherheits)\b",
]
WORK_AUTH = [
    r"\b(?:unrestricted|existing|current|already)\b.{0,35}\b(?:work authorization|right to work|work permit|working rights)\b",
    r"\b(?:must|need|required to)\b.{0,50}\b(?:right to work|authorized to work|work permit)\b",
    r"\b(?:no|not providing|cannot provide|unable to provide)\s+(?:visa\s+)?sponsorship\b",
    r"\b(?:visum|arbeitserlaubnis|aufenthaltserlaubnis)\b.{0,45}\b(?:bereits|vorhanden|vorausgesetzt|erforderlich)\b",
]

# A high seniority job can still be worth reading. We flag, never silently exclude.
SPECIALIST_YEARS = [
    r"\b(?:minimum(?: of)?|at least|more than|over|mindestens)\s*(?:[7-9]|1\d)\s*\+?\s*(?:years|jahre)\b.{0,90}\b(?:aerospace|aviation|semiconductor|battery systems?|aircraft|wafer|industrial production|cleanroom|luftfahrt|halbleiter)\b",
    r"\b(?:[7-9]|1\d)\s*[-–]\s*(?:[8-9]|1\d)\s*(?:years|jahre)\b.{0,90}\b(?:aerospace|aviation|semiconductor|aircraft|wafer|luftfahrt|halbleiter)\b",
]


def matches_any(text: str, expressions: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in expressions)


def screening_notes(job: dict) -> dict:
    text = str(job.get("description") or "")
    flags: list[str] = []
    citizenship = matches_any(text, CITIZENSHIP_REQUIREMENT)
    if citizenship:
        flags.append("Citizenship requirement stated — verify exact eligibility")
    if matches_any(text, EXPORT_CONTROL):
        flags.append("Export-control terms — check role-specific rules")
    if matches_any(text, SECURITY_CLEARANCE):
        flags.append("Security clearance mentioned — verify requirements")
    if matches_any(text, WORK_AUTH):
        flags.append("Work authorization / sponsorship — verify")
    if matches_any(text, SPECIALIST_YEARS):
        flags.append("Specialized experience requirement — check mandatory years")
    status = job.get("location_status")
    if status == "verify_location":
        flags.append("Worksite unclear or multiple countries — verify")
    elif status == "outside":
        flags.append("Advertised worksite outside Germany — verify")
    if job.get("source_mode") == "html_fallback" or not text.strip():
        flags.append("Title-only / missing description — verify full advertisement")
    return {"screening_flags": flags, "citizenship_restriction_detected": citizenship}


def screen_state(state: dict) -> dict:
    for job in state.get("jobs", {}).values():
        job.update(screening_notes(job))
    return state


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    screen_state(state)
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The monitor writes a sorted public snapshot; preserve its order and source
    # status instead of rebuilding from state in a new location.
    visible = json.loads(PUBLIC.read_text(encoding="utf-8"))
    for job in visible.get("jobs", []):
        job.update(screening_notes(job))
    PUBLIC.write_text(json.dumps(visible, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added conservative screening flags to {len(visible.get('jobs', []))} public vacancies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

