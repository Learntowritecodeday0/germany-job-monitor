"""Verify documented materials-source additions and frontend theme hooks.

Keep copy wording flexible: test behavior and structural intent, not specific
explanatory sentences (previously caused a failing deployment).
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import monitor

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "companies.json").read_text(encoding="utf-8"))
BY_NAME = {c["name"]: c for c in CFG["companies"]}
HTML = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "docs" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "docs" / "theme.js").read_text(encoding="utf-8")


class MaterialsSourcesAndThemeTests(unittest.TestCase):
    def test_new_official_recruitment_sources(self):
        expectations = {
            "E-Lyte Innovations": ("personio", "e-lyte", "e-lyte.jobs.personio.de"),
            "CuspAI": ("ashby", "cuspai", "jobs.ashbyhq.com"),
        }
        self.assertEqual(len(BY_NAME), len(CFG["companies"]))
        for name, (platform, slug, host) in expectations.items():
            with self.subTest(company=name):
                c = BY_NAME[name]
                self.assertEqual(c["platform"], platform)
                self.assertEqual(c["slug"], slug)
                self.assertTrue(c["careers_url"].startswith("https://" + host))
                self.assertTrue(c["focus"])
                self.assertTrue(c["note"])

    def test_initial_discovery_is_baseline_and_failed_source_is_isolated(self):
        company = BY_NAME["E-Lyte Innovations"]
        sample = {"key": "personio:e-lyte:123", "company": company["name"],
                  "title": "Labor Scientist", "description": "Laboratory chemistry",
                  "location": "Münster", "country": "Germany",
                  "url": company["careers_url"] + "/job/123", "published_at": None}
        config = {"companies": [company]}
        with patch.object(monitor, "fetch_company", return_value=[sample]):
            state = monitor.update(config, {"jobs": {}, "sources": {}}, "2026-11-15T21:30:00+00:00")
        self.assertTrue(state["jobs"][sample["key"]]["at_startup"])
        with patch.object(monitor, "fetch_company", side_effect=ValueError("Unavailable")):
            state = monitor.update(config, state, "2026-11-15T22:00:00+00:00")
        self.assertEqual(state["sources"][company["name"]]["status"], "error")
        self.assertTrue(state["jobs"][sample["key"]]["active"])

    def test_theme_has_system_default_and_accessible_manual_choice(self):
        self.assertIn('src="theme.js"', HTML)
        self.assertIn('id="themeMode"', HTML)
        self.assertIn('for="themeMode"', HTML)
        for value in ('value="system"', 'value="light"', 'value="dark"'):
            self.assertIn(value, HTML)
        self.assertIn("prefers-color-scheme:dark", CSS)
        self.assertIn(':root[data-theme="dark"]', CSS)
        self.assertIn(':root[data-theme="light"]', CSS)
        self.assertIn("localStorage", JS)
        self.assertIn("root.removeAttribute('data-theme')", JS)
        self.assertIn("DOMContentLoaded", JS)

    def test_dark_palette_covers_job_and_application_sections(self):
        for selector in (".job", ".summary article", ".application-summary article",
                         ".application-table th", ".requirement-review",
                         ".chip.strong", ".theme-switch select"):
            self.assertIn(selector, CSS)


if __name__ == "__main__":
    unittest.main()
