"""Tests for DELO's official public Workday vacancies; no live network requests."""
import json
from http.client import IncompleteRead
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import location_detail
import monitor
from workday_adapter import (workday_paths, normalize_workday_job,
                             enrich_workday_job)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/companies.json").read_text(encoding="utf-8"))
DELO = next(c for c in CONFIG["companies"] if c["name"] == "DELO")
CHEM = {
    "title": "Entwicklungschemiker Klebstoffe (m/w/d)",
    "externalPath": "/job/Windach/Entwicklungschemiker-Klebstoffe_R001",
    "locationsText": "Windach",
    "postedOn": "Posted 2 Days Ago",
}
OTHER = {
    "title": "Vertriebsassistenz",
    "externalPath": "/job/Windach/Vertriebsassistenz_R002",
    "locationsText": "Windach",
    "postedOn": "Posted Today",
}
DETAIL = {"jobPostingInfo": {
    "title": CHEM["title"],
    "jobDescription": "<h2>Ihre Aufgaben</h2><p>Entwicklung von Klebstoffrezepturen, Laborversuche und "
                      "Prozessoptimierung mit Versuchsplanung und analytischen Methoden.</p>"
                      "<h2>Ihr Profil</h2><p>Studium der Chemie oder Materialwissenschaften "
                      "mit experimenteller Laborerfahrung und Dokumentation.</p>"
}}


class DELOWorkdayTests(TestCase):
    def test_workday_url_is_derived_from_official_career_link(self):
        self.assertEqual(DELO["careers_url"],
                         "https://delo.wd103.myworkdayjobs.com/en-US/DELO-Jobs")
        api, public = workday_paths(DELO)
        self.assertEqual(api, "https://delo.wd103.myworkdayjobs.com/wday/cxs/delo/DELO-Jobs")
        self.assertEqual(public, DELO["careers_url"])

    def test_external_urls_and_unsafe_paths_rejected(self):
        for url in ["http://delo.wd103.myworkdayjobs.com/DELO-Jobs",
                    "https://another.example.com/en-US/DELO-Jobs",
                    "https://delo.wd103.myworkdayjobs.com/en-US/DELO-Jobs/admin"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                workday_paths({**DELO, "careers_url": url})
        for path in ["https://bad.example/job/123", "//attacker.example/job/123",
                     "/job/../other-id", "/job/Windach/test?id=2", "/job/%2fetc/test"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                normalize_workday_job(DELO, {**CHEM, "externalPath": path})

    def test_normalization_preserves_explicit_worksite_without_invented_date(self):
        job = normalize_workday_job(DELO, CHEM)
        self.assertEqual(job["published_at"], None)
        self.assertEqual(job["location"], "Windach")
        self.assertEqual(job["country"], "")
        self.assertEqual(job["source_mode"], "api_list_only")
        self.assertTrue(job["url"].endswith(CHEM["externalPath"]))
        self.assertEqual(monitor.location_status(job), "germany")
        site = location_detail.format_worksites(job)
        self.assertEqual((site["worksite_city"], site["worksite_state"],
                          site["worksite_country"]), ("Windach", "Bayern", "Germany"))

    def test_two_postings_and_one_detail_request(self):
        with patch.object(monitor, "post_public_json",
                          return_value={"total": 2, "jobPostings": [CHEM, OTHER]}) as post:
            with patch.object(monitor, "get_json", return_value=DETAIL) as get:
                jobs = monitor.fetch_company(DELO)
        self.assertEqual(len(jobs), 2)
        post.assert_called_once_with(
            "https://delo.wd103.myworkdayjobs.com/wday/cxs/delo/DELO-Jobs/jobs",
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""})
        self.assertEqual(get.call_count, 1)
        self.assertTrue(get.call_args.args[0].endswith(CHEM["externalPath"]))
        self.assertEqual(jobs[0]["source_mode"], "api_detail")
        self.assertIn("Klebstoffrezepturen", jobs[0]["description"])
        self.assertEqual(jobs[1]["source_mode"], "api_list_only")
        self.assertNotIn("_workday_path", jobs[0])
        self.assertIsNone(jobs[0]["published_at"])

    def test_page_two_is_requested_and_relative_dates_ignored(self):
        first = [{**OTHER, "externalPath": f"/job/Windach/Sales_R{i}"} for i in range(20)]
        last = [{**OTHER, "externalPath": "/job/Windach/Sales_R20"}]
        pages = [{"total": 21, "jobPostings": first},
                 {"total": 0, "jobPostings": last}]
        with patch.object(monitor, "post_public_json", side_effect=pages) as post:
            with patch.object(monitor, "get_json") as get:
                jobs = monitor.fetch_company(DELO)
        self.assertEqual(len(jobs), 21)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[1].args[1]["offset"], 20)
        get.assert_not_called()
        self.assertTrue(all(x["published_at"] is None for x in jobs))

    def test_empty_or_malformed_response_does_not_invent_zero_vacancies(self):
        with patch.object(monitor, "post_public_json", return_value={"total": 3}):
            with self.assertRaises(ValueError):
                monitor.fetch_company(DELO)
        with patch.object(monitor, "post_public_json",
                          return_value={"total": 3, "jobPostings": []}):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                monitor.fetch_company(DELO)
        with patch.object(monitor, "post_public_json",
                          return_value={"total": 0, "jobPostings": []}):
            self.assertEqual(monitor.fetch_company(DELO), [])

    def test_incomplete_optional_detail_retains_job_title(self):
        with patch.object(monitor, "post_public_json",
                          return_value={"total": 1, "jobPostings": [CHEM]}):
            with patch.object(monitor, "get_json", side_effect=IncompleteRead(b"part")):
                jobs = monitor.fetch_company(DELO)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["source_mode"], "api_list_only")

    def test_mismatched_detail_not_used_as_chemistry_evidence(self):
        job = normalize_workday_job(DELO, CHEM)
        enrich_workday_job(job, {"jobPostingInfo": {**DETAIL["jobPostingInfo"], "title": "Another role"}})
        self.assertEqual(job["source_mode"], "api_list_only")
        self.assertEqual(job["description"], "")

    def test_limited_window_preserves_older_jobs_on_successful_scan(self):
        old = normalize_workday_job(DELO, CHEM)
        new = normalize_workday_job(DELO, OTHER)
        with patch.object(monitor, "fetch_company", return_value=[old]):
            state = monitor.update({"companies": [DELO]}, {"jobs": {}, "sources": {}},
                                   "2026-11-16T10:00:00+00:00")
        with patch.object(monitor, "fetch_company", return_value=[new]):
            state = monitor.update({"companies": [DELO]}, state, "2026-11-16T13:00:00+00:00")
        self.assertTrue(state["jobs"][old["key"]]["active"])
        self.assertTrue(state["sources"]["DELO"]["recent_window"])
        self.assertEqual(state["sources"]["DELO"]["source_mode"], "recent_window")
        self.assertEqual(state["jobs"][old["key"]]["reopen_count"], 0)

    def test_connection_error_is_source_error_without_losing_history(self):
        with patch.object(monitor, "fetch_company", return_value=[normalize_workday_job(DELO, CHEM)]):
            state = monitor.update({"companies": [DELO]}, {"jobs": {}, "sources": {}},
                                   "2026-11-16T10:00:00+00:00")
        with patch.object(monitor, "fetch_company", side_effect=ValueError("Blocked")):
            state = monitor.update({"companies": [DELO]}, state,
                                   "2026-11-16T13:00:00+00:00")
        self.assertEqual(state["sources"]["DELO"]["status"], "error")
        self.assertTrue(next(iter(state["jobs"].values()))["active"])


if __name__ == "__main__":
    import unittest
    unittest.main()
