"""Regress country-filtered public SmartRecruiters listings for large employers."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

SOURCE=next(c for c in json.loads((Path(__file__).resolve().parents[1]/'config/companies.json').read_text())['companies'] if c['name']=='SGS')

def record(ident="744000001", title="Chemiker Laboranalytik", country="de"):
    return {"id":ident, "name":title,
            "location":{"city":"Hamburg", "region":"Hamburg", "country":country},
            "postingUrl":f"https://jobs.smartrecruiters.com/SGS/{ident}",
            "releasedDate":"2026-11-16T10:00:00Z"}


class SGSFeedTests(unittest.TestCase):
    def test_official_source_url_country_filter(self):
        self.assertEqual(SOURCE["platform"],"smartrecruiters")
        self.assertEqual(SOURCE["slug"],"SGS")
        self.assertEqual(SOURCE["country_filter"],"de")

    def test_list_query_uses_country_de_and_enriches_scientific_details(self):
        listing={"content":[record()], "totalFound":1}
        detail={"jobAd":{"sections":{"jobDescription":{"text":"<p>Perform analytical laboratory testing with instrument verification and quality controls.</p>"},"qualifications":{"text":"<p>Degree in chemistry; experience with HPLC is preferred.</p>"}}}}
        with patch.object(monitor,"get_json",side_effect=[listing,detail]) as get:
            jobs=monitor.fetch_company(SOURCE)
        self.assertEqual(len(jobs),1)
        self.assertEqual(get.call_count,2)
        self.assertIn("limit=100&offset=0&country=de",get.call_args_list[0].args[0])
        self.assertEqual(jobs[0]["country"],"de")
        self.assertEqual(jobs[0]["source_mode"],"api_detail")
        self.assertIn("laboratory testing",jobs[0]["description"])

    def test_filtered_pagination_is_bounded_and_complete(self):
        items=[record(str(n),title="Job "+str(n)) for n in range(100)]
        pages=[{"content":items,"totalFound":101},{"content":[record("101",title="Job 101")],"totalFound":101}]
        with patch.object(monitor,"get_json",side_effect=pages) as get:
            jobs=monitor.fetch_company(SOURCE)
        self.assertEqual(len(jobs),101)
        self.assertEqual(get.call_count,2)
        self.assertIn("offset=100&country=de",get.call_args_list[1].args[0])

    def test_country_filter_ignored_raises_instead_of_claiming_coverage(self):
        listing={"content":[record(country="us")],"totalFound":1}
        with patch.object(monitor,"get_json",return_value=listing):
            with self.assertRaisesRegex(ValueError,"non-German"):
                monitor.fetch_company(SOURCE)

    def test_invalid_country_filter_does_not_contact_api(self):
        with patch.object(monitor,"get_json") as get:
            with self.assertRaisesRegex(ValueError,"country filter"):
                monitor.fetch_company({**SOURCE, "country_filter":"eu"})
        get.assert_not_called()

    def test_missing_total_found_never_counts_as_complete(self):
        with patch.object(monitor,"get_json",return_value={"content":[record()]}):
            with self.assertRaisesRegex(ValueError,"totalFound"):
                monitor.fetch_company(SOURCE)

if __name__=="__main__":
    unittest.main()
