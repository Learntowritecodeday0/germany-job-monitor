"""Source coverage and Personio XML description recovery regressions."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

ROOT = Path(__file__).resolve().parents[1]
COMPANIES = json.loads((ROOT / "config" / "companies.json").read_text())["companies"]
DETAIL = """<html><body><main><h1>R&amp;D &amp; Scale-up Food Scientist [m/f/d]</h1>
<h2>Your Tasks</h2><p>Develop and optimize laboratory formulations and record
instrumental measurements. Use experimental design to compare particle size and
stability across candidate formulations.</p>
<h2>Your Profile</h2><p>Degree in material science or food science and experience
with analytical tests and process optimization.</p>
<h2>Why Us</h2><p>Free snacks and company events.</p></main></body></html>"""


def sample(title="R&D & Scale-up Food Scientist [m/f/d]", number="123"):
    return {"key": "personio:test:" + number, "platform": "personio",
            "company": "Example", "title": title, "url": "https://example.jobs.personio.de/job/" + number,
            "description": "", "location": "Berlin", "country": "Germany", "published_at": None}


class IncompletePersonioTests(unittest.TestCase):
    def test_new_public_laboratory_sources_are_unique(self):
        by_name = {x["name"]: x for x in COMPANIES}
        for name, host in [
            ("Tentamus Group", "tentamus.jobs.personio.de"),
            ("Hohenstein", "hohenstein.jobs.personio.de"),
            ("CR3-Kaffeeveredelung", "cr3-kaffeeveredelung.jobs.personio.de"),
            ("EyeSense", "eyesense.jobs.personio.de"),
        ]:
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["platform"], "personio")
                self.assertEqual(by_name[name]["careers_url"], "https://" + host)
        self.assertEqual(len(COMPANIES), len({x["name"] for x in COMPANIES}))

    def test_xml_missing_duties_can_recover_official_detail(self):
        original = sample()
        with patch.object(monitor, "get_html", return_value=DETAIL) as request:
            result = monitor.enrich_personio_incomplete([original])
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result[0]["source_mode"], "html_detail")
        self.assertIn("laboratory formulations", result[0]["description"])
        self.assertNotIn("Free snacks", result[0]["description"])
        self.assertEqual(result[0]["location"], "Berlin")
        self.assertEqual(result[0]["country"], "Germany")
        self.assertIsNone(result[0]["published_at"])

    def test_unrelated_and_already_complete_jobs_are_not_refetched(self):
        filled = {**sample(number="1"), "description": "Already confirmed job information. " * 12}
        other = sample(title="Marketing Controller", number="2")
        with patch.object(monitor, "get_html") as request:
            result = monitor.enrich_personio_incomplete([filled, other])
        request.assert_not_called()
        self.assertEqual(result, [filled, other])

    def test_missing_official_detail_does_not_remove_listing(self):
        item = sample()
        failure = HTTPError(item["url"], 404, "Not found", {}, None)
        with patch.object(monitor, "get_html", side_effect=failure):
            result = monitor.enrich_personio_incomplete([item])
        self.assertEqual(result, [item])

    def test_detail_reads_are_bounded(self):
        jobs = [sample(number=str(n)) for n in range(5)]
        with patch.object(monitor, "get_html", return_value=DETAIL) as request, \
             patch.object(monitor.time, "sleep"):
            result = monitor.enrich_personio_incomplete(jobs, max_pages=1)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(sum(bool(j.get("source_mode")) for j in result), 1)


if __name__ == "__main__":
    unittest.main()
