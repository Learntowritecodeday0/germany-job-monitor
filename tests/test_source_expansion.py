import json
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "companies.json").read_text(encoding="utf-8"))
NEW = {
    "Phlair": "ashby",
    "Differential Bio": "ashby",
    "BIOWEG": "personio",
    "DWI Leibniz Institute for Interactive Materials": "personio",
    "aevoloop": "personio",
    "UNICOR": "personio",
    "Project Eaden": "personio",
    "Hades Mining": "personio",
    "VERTANICAL": "ashby",
    "Sunday Natural": "personio",
}

class ExpansionTests(unittest.TestCase):
    def test_all_47_sources_unique(self):
        self.assertEqual(len(CFG["companies"]), 48)
        self.assertEqual(len({x["name"] for x in CFG["companies"]}), 47)
        self.assertEqual(len({(x["platform"], x["slug"]) for x in CFG["companies"]}), 47)
    def test_added_sources_have_supported_platforms_and_https_url(self):
        byname = {x["name"]: x for x in CFG["companies"]}
        for name,platform in NEW.items():
            with self.subTest(name=name):
                self.assertEqual(byname[name]["platform"], platform)
                self.assertTrue(byname[name]["careers_url"].startswith("https://"))
                self.assertTrue(byname[name]["slug"])
    def test_first_time_discovery_is_baseline_not_alert(self):
        sample = {"key":"ashby:phlair:https://jobs.ashbyhq.com/phlair/test", "company":"Phlair", "title":"Chemical R&D Scientist", "location":"Munich", "country":"Germany", "description":"silica particle analysis and DoE", "url":"https://jobs.ashbyhq.com/phlair/test", "published_at":None}
        company = next(x for x in CFG["companies"] if x["name"]=="Phlair")
        with patch.object(monitor,"fetch_company",return_value=[sample]):
            result = monitor.update({"companies":[company]}, {"jobs":{},"sources":{}}, "2026-11-11T15:00:00+00:00")
        self.assertTrue(result["jobs"][sample["key"]]["at_startup"])
    def test_failed_source_does_not_remove_existing_jobs(self):
        from urllib.error import HTTPError
        sample = {"key":"personio:bioweg:123", "company":"BIOWEG", "title":"Materials Scientist", "location":"Düsseldorf", "active":True, "first_detected":"2026-11-10T15:00:00+00:00"}
        company = next(x for x in CFG["companies"] if x["name"]=="BIOWEG")
        state = {"jobs": {sample["key"]:sample},"sources":{"BIOWEG":{"initialized":True,"status":"ok","count":1}}}
        with patch.object(monitor,"fetch_company",side_effect=HTTPError("https://example.com",404,"Not Found",{},None)):
            result = monitor.update({"companies":[company]},state,"2026-11-11T15:00:00+00:00")
        self.assertTrue(result["jobs"][sample["key"]]["active"])
        self.assertEqual(result["sources"]["BIOWEG"]["status"],"error")

if __name__ == "__main__": unittest.main()
