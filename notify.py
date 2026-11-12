#!/usr/bin/env python3
"""Send opt-in job alerts by SMTP, using GitHub Actions repository secrets.

No credentials, recipient address, or email body are written to the public site.
A successful send adds job IDs to data/state.json to avoid repeated alerts.
This script is deliberately separate from monitor.py to preserve feed behavior.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

STATE = Path(__file__).resolve().parent / "data" / "state.json"
MAX_JOBS_PER_MESSAGE = 10


def candidates(state):
    """Prioritize new, non-baseline, active, degree-oriented high-fit listings."""
    sent = state.get("alerts_sent", {})
    started_at = state.get("alerts_started_at")
    found = []
    for key, job in state.get("jobs", {}).items():
        if not job.get("active", False):
            continue
        if job.get("at_startup", True):
            continue
        if started_at is not None and (job.get("first_detected") or "") <= started_at:
            continue
        if job.get("hide_by_default", False):
            continue
        # A public job advert can state a citizenship restriction. Do not
        # alert automatically until the requirement is reviewed. This is NOT
        # a decision about any particular applicant.
        if job.get("citizenship_restriction_detected", False):
            continue
        if job.get("location_status") == "outside":
            continue
        if job.get("source_mode") in ("html_fallback", "recent_title_only", "api_list_only"):
            continue
        if job.get("match_band") != "Review first":
            continue
        if key in sent:
            continue
        found.append(job)
    return sorted(found, key=lambda j: j.get("first_detected") or "")


def email_content(jobs, is_test=False):
    msg = EmailMessage()
    if is_test:
        msg["Subject"] = "Germany Job Monitor — test email"
        msg.set_content(
            "Test successful: GitHub Actions can send email notifications.\n\n"
            "Future emails will be sent only for newly detected jobs labelled 'Review first'.\n"
            "Existing startup vacancies are excluded. Screening is not an eligibility determination.\n"
        )
        return msg
    count = len(jobs)
    msg["Subject"] = f"Germany Job Monitor — {count} new job{'s' if count != 1 else ''} to review"
    lines = [
        f"{count} newly detected high-priority job{'s' if count != 1 else ''}:",
        "",
        "These are keyword-screening matches, not verified eligibility or hiring-fit decisions.",
        "Check essential qualifications, citizenship requirements, work authorization and actual worksite.",
        "",
    ]
    for i, job in enumerate(jobs, 1):
        lines += [
            f"{i}. {job.get('title', 'Untitled')} — {job.get('company', '')}",
            f"   Location: {job.get('location') or 'Not confirmed'}",
            f"   First detected: {job.get('first_detected', '')}",
            f"   Relevant topics: {', '.join(job.get('matched_topics', [])) or 'Not specified'}",
            f"   Link: {job.get('url', '')}",
            "",
        ]
    lines += ["Existing listings from the initial scan are not included."]
    msg.set_content("\n".join(lines))
    return msg


def smtp_send(msg, *, username, password, recipient, host="smtp.gmail.com", port=465):
    msg["From"] = username
    msg["To"] = recipient
    context = ssl.create_default_context()
    # Use Gmail SMTP over TLS from the beginning; do not fall back to plaintext.
    with smtplib.SMTP_SSL(host, port, timeout=25, context=context) as server:
        server.login(username, password)
        server.send_message(msg)


def main():
    test_requested = os.environ.get("SEND_TEST_EMAIL", "").strip().lower() in ("true", "1", "yes")
    username = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").replace(" ", "").strip()
    recipient = os.environ.get("ALERT_TO", "").strip()
    if not all((username, password, recipient)):
        if test_requested:
            print("ERROR: Missing one or more repository secrets: SMTP_USER, SMTP_PASSWORD, ALERT_TO", file=sys.stderr)
            return 1
        print("Email alerts not configured yet; skipping without changing monitoring history.")
        return 0

    if not STATE.exists():
        print("ERROR: Missing monitoring state file", file=sys.stderr)
        return 1
    state = json.loads(STATE.read_text(encoding="utf-8"))
    # On first activation, mark all existing listings as historical. Even jobs
    # first seen after the monitor's original startup are not emailed retroactively.
    first_activation = "alerts_started_at" not in state
    if first_activation:
        state["alerts_started_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Email baseline initialized; all existing listings excluded from alerts.")

    if test_requested:
        smtp_send(email_content([], is_test=True), username=username, password=password, recipient=recipient)
        print("Test email sent. Check the destination inbox (and Spam folder).")

    jobs = candidates(state)[:MAX_JOBS_PER_MESSAGE]
    if not jobs:
        print("No new high-priority jobs requiring email alerts.")
        return 0
    smtp_send(email_content(jobs), username=username, password=password, recipient=recipient)
    state.setdefault("alerts_sent", {})
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for job in jobs:
        state["alerts_sent"][job["key"]] = timestamp
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Sent one digest for {len(jobs)} newly detected priority jobs and recorded delivery IDs.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (smtplib.SMTPException, OSError, ValueError) as error:
        # Do not print message contents, passwords or recipients.
        print(f"EMAIL ERROR ({type(error).__name__}): SMTP delivery failed; alert IDs were not marked as sent.", file=sys.stderr)
        sys.exit(1)
