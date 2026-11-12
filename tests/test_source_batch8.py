"""Regression tests for optional Softgarden source expansion (no live network)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "companies.json").read_text(encoding="utf-8"))

class SourceBatch8(unittest.TestCase):
    def test_names_and_slugs_unique(self):
        rows = CFG["companies"]
        self.assertEqual(len({x["name"].casefold() for x in rows}), len(rows))
        self.assertEqual(len({(x["platform"], x["slug"]) for x in rows}), len(rows))

    def test_new_sources_have_public_feed_urls(self):
        slugs = {"ineos-solvents", "das-ee", "palplast", "horn-bauer"}
        rows = [x for x in CFG["companies"] if x["slug"] in slugs]
        self.assertEqual({x["slug"] for x in rows}, slugs)
        for row in rows:
            with self.subTest(source=row["name"]):
                self.assertEqual(row["platform"], "softgarden")
                self.assertTrue(row["feed_url"].startswith("https://"))
                self.assertTrue(row["feed_url"].endswith("/jobs.feed.json"))
                self.assertIn("career.softgarden.de", row["feed_url"])

    def test_softgarden_fixture_compatible(self):
        # Test the live code's existing adapter with an offline DataFeed fixture.
        import monitor
        c = next(x for x in CFG["companies"] if x["slug"] == "ineos-solvents")
        fixture = {"@type":"DataFeed", "dataFeedElement":[{"dateModified":"2026-11-12T09:00:00Z", "item":{
            "@type":"JobPosting", "identifier":{"value":42},
            "title":"Labor Scientist – Silica", "description":"<p>Analyze particles</p>",
            "url":"https://ineos-solvents.career.softgarden.de/jobs/42/example",
            "datePosted":"2026-11-11T09:00:00Z",
            "jobLocation":{"address":{"addressLocality":"Marl","addressRegion":"Nordrhein-Westfalen","addressCountry":"Deutschland"}}
        }}]}
        jobs = monitor.parse_softgarden(c, fixture)
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]["key"], "softgarden:ineos-solvents:42")
        self.assertIn("Marl", jobs[0]["location"])
        self.assertIn("Analyze particles", jobs[0]["description"])

if __name__ == "__main__":
    unittest.main()
