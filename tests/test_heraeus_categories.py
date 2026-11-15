"""Regression tests for bounded official Heraeus R&D + Lab public listings."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import monitor
from heraeus_adapter import parse_heraeus_category, enrich_heraeus_job

C=json.loads((Path(__file__).resolve().parents[1]/"config/companies.json").read_text())
H=next(x for x in C["companies"] if x["name"]=="Heraeus — research and analytics categories")
PAGE='''<html><h1>17 found Research & Development Jobs</h1><a href="/en/job/hanau/chemical-process-engineer/3105/40112233">Chemical Process Engineer (m/f/d)</a><a href="/en/job/dresden/materials-scientist/3105/40112234">Materials Scientist</a><a href="/en/job/buford/us-process-engineer/3105/40112235">US Process Engineer</a><a href="https://imposter.example/en/job/hanau/fake/3105/99999">Imposter</a></html>'''
LAB='''<h1>5 found Lab & Analytics Jobs</h1><a href="https://jobs.heraeus.com/en/job/hanau/chemical-process-engineer/3105/40112233">Chemical Process Engineer (m/f/d)</a><a href="/en/job/wehrheim/analytical-chemist/3105/40112236">Analytical Chemist</a>'''
DETAIL='''<html><h1>Chemical Process Engineer (m/f/d)</h1><h2>Your responsibilities</h2><p>Develop laboratory processes for particle materials, improve experimental methods and evaluate results by thermal analysis, microscopy and laboratory measurements.</p><h2>Your qualifications</h2><p>Degree in chemistry or materials science. Experience with research documentation, experimental planning and material properties.</p><h2>Interested? Apply now</h2></html>'''

class HeraeusSourcesTests(unittest.TestCase):
    def test_only_official_german_links_and_stable_ids(self):
        jobs=parse_heraeus_category(H,PAGE)
        self.assertEqual(len(jobs),2)
        self.assertEqual({x["key"] for x in jobs},{"heraeus_categories:heraeus-research:40112233","heraeus_categories:heraeus-research:40112234"})
        self.assertTrue(all(x["country"]=="Germany" for x in jobs))
        self.assertTrue(all(x["published_at"] is None for x in jobs))
        self.assertTrue(all(x["source_mode"]=="recent_title_only" for x in jobs))

    def test_detail_does_not_invent_description_or_date(self):
        job=parse_heraeus_category(H,PAGE)[0]
        enrich_heraeus_job(job,DETAIL)
        self.assertEqual(job["source_mode"],"html_detail")
        self.assertIn("materials science",job["description"])
        self.assertIsNone(job["published_at"])
        other=parse_heraeus_category(H,PAGE)[1]
        enrich_heraeus_job(other,DETAIL)
        self.assertEqual(other["source_mode"],"recent_title_only")

    def test_changed_listing_is_error_not_zero(self):
        with self.assertRaisesRegex(ValueError,"no recognized official job links"):
            parse_heraeus_category(H,"<html><h1>Access denied</h1></html>")

    def test_fetch_deduplicates_categories_and_stays_bounded(self):
        with patch.object(monitor,"get_html",side_effect=[PAGE,LAB,DETAIL,DETAIL,DETAIL]) as get:
            jobs=monitor.fetch_company(H)
        self.assertEqual(len(jobs),3)
        self.assertEqual(get.call_count,5)
        self.assertEqual(get.call_args_list[0].args[0],H["category_urls"][0])
        self.assertEqual(get.call_args_list[1].args[0],H["category_urls"][1])

    def test_partial_categories_do_not_close_missing_jobs(self):
        first=parse_heraeus_category(H,PAGE)[0]
        second=parse_heraeus_category(H,LAB)[1]
        with patch.object(monitor,"fetch_company",return_value=[first]):
            state=monitor.update({"companies":[H]},{"jobs":{},"sources":{}},"2026-11-15T14:00:00+00:00")
        with patch.object(monitor,"fetch_company",return_value=[second]):
            state=monitor.update({"companies":[H]},state,"2026-11-15T16:00:00+00:00")
        self.assertTrue(state["jobs"][first["key"]]["active"])
        self.assertEqual(state["jobs"][first["key"]]["reopen_count"],0)
        self.assertTrue(state["sources"][H["name"]]["recent_window"])
        self.assertEqual(state["sources"][H["name"]]["source_mode"],"recent_window")

    def test_feed_error_keeps_existing_jobs(self):
        first=parse_heraeus_category(H,PAGE)[0]
        with patch.object(monitor,"fetch_company",return_value=[first]):
            state=monitor.update({"companies":[H]},{"jobs":{},"sources":{}},"2026-11-15T14:00:00+00:00")
        with patch.object(monitor,"fetch_company",side_effect=ValueError("Markup unavailable")):
            state=monitor.update({"companies":[H]},state,"2026-11-15T16:00:00+00:00")
        self.assertEqual(state["sources"][H["name"]]["status"],"error")
        self.assertTrue(state["jobs"][first["key"]]["active"])

if __name__=="__main__":
    unittest.main()
