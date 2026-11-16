"""Source-configuration regression tests for additional chemistry/materials employers."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"config/companies.json").read_text(encoding="utf-8"))
HTML=(ROOT/"docs/index.html").read_text(encoding="utf-8")
NEW={"Lohmann Tapes":"lohmann-tapes","MÜNZING CHEMIE":"munzing"}

class ChemistryEmployersTest(unittest.TestCase):
    def test_unique_company_sources(self):
        companies=CONFIG["companies"]
        self.assertEqual(len(companies),len({c["name"] for c in companies}))
        self.assertEqual(len(companies),len({(c["platform"],c["slug"]) for c in companies}))

    def test_new_sources_have_expected_board_and_feed(self):
        byname={x["name"]:x for x in CONFIG["companies"]}
        for name,slug in NEW.items():
            with self.subTest(name=name):
                company=byname[name]
                self.assertEqual(company["platform"],"softgarden")
                self.assertEqual(company["slug"],slug)
                self.assertEqual(urlparse(company["careers_url"]).hostname, slug+".softgarden.io")
                self.assertEqual(urlparse(company["feed_url"]).hostname,slug+".career.softgarden.de")
                self.assertTrue(company.get("focus"))
                self.assertIn("first",company["note"].lower())

    def test_manual_employers_are_not_falsely_monitored(self):
        # Verify actual configuration membership, not mutable explanatory copy.
        self.assertIn('<section class="manual-sources"', HTML)
        section = HTML.split('<section class="manual-sources"', 1)[1].split("</section>", 1)[0]
        manual = ("BYK", "WACKER", "Evonik", "Bruker", "LUM",
                  "BASF", "Henkel", "Covestro", "Clariant", "SCHOTT", "LANXESS")
        configured = {company["name"] for company in CONFIG["companies"]}
        for name in manual:
            with self.subTest(name=name):
                self.assertIn(name, section)
                self.assertNotIn(name, configured)
        self.assertIn("DELO", configured)
        self.assertTrue(any(name.startswith("Heraeus") for name in configured))


if __name__=="__main__":unittest.main()
