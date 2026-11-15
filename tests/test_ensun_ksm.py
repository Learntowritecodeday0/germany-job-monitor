"""Tests for official KSM listings and curated Ensun materials employers."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import monitor
from ksm_adapter import parse_ksm_listing, enrich_ksm_job

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config/companies.json").read_text(encoding="utf-8"))
K=next(c for c in CFG["companies"] if c["name"]=="KSM Castings")
PAGE='''<html><h1>Stellenangebote</h1>
<a href="/stellenanzeige/prozessingenieur-mechanische-bearbeitung-m-w-d-x/">Prozessingenieur Mechanische Bearbeitung (m/w/d/x)</a>
<a href="https://karriere.ksmcastings.com/stellenanzeige/analytiker-in-werkstoffpruefung/">Analytiker in Werkstoffprüfung</a>
<a href="https://example.invalid/stellenanzeige/fake/">Fake</a></html>'''
DETAIL='''<html><h1>Prozessingenieur Mechanische Bearbeitung (m/w/d/x)</h1>
<h2>Standort Bergisches Land</h2><h3>Das gehört zu Ihren Aufgaben</h3>
<p>Prozessdefinition und Optimierung für Aluminiumteile und Qualitätskontrolle. Systematische Auswertung von Kennzahlen zur Identifikation von Abweichungen. Produktionsprozesse verbessern.</p>
<h3>Das bringen Sie mit</h3><p>Erfahrung in industrieller Zerspanung und Lean Production.</p>
<h3>Ihre Benefits</h3></html>'''

class KSMAndEnsunTests(unittest.TestCase):
    def test_only_official_links_without_fabricated_dates(self):
        jobs=parse_ksm_listing(K,PAGE)
        self.assertEqual(len(jobs),2)
        self.assertTrue(all(x["url"].startswith("https://karriere.ksmcastings.com/stellenanzeige/") for x in jobs))
        self.assertTrue(all(x["published_at"] is None for x in jobs))

    def test_unreadable_listing_is_error(self):
        with self.assertRaises(ValueError):
            parse_ksm_listing(K,"<h1>No usable results</h1>")

    def test_optional_detail_preserves_record_on_disconnect(self):
        from http.client import IncompleteRead
        with patch.object(monitor,"get_html",side_effect=[PAGE,IncompleteRead(b"part"),DETAIL]):
            jobs=monitor.fetch_company(K)
        self.assertEqual(len(jobs),2)
        self.assertEqual(jobs[0]["source_mode"],"html_fallback")

    def test_details_dont_invent_dates(self):
        j=parse_ksm_listing(K,PAGE)[0]
        enrich_ksm_job(j,DETAIL)
        self.assertIsNone(j["published_at"])
        self.assertIn("Aluminiumteile",j["description"])

    def test_failed_source_preserves_earlier_jobs(self):
        j=parse_ksm_listing(K,PAGE)[0]
        with patch.object(monitor,"fetch_company",return_value=[j]):
            state=monitor.update({"companies":[K]},{"jobs":{},"sources":{}},"2026-11-15T21:00:00+00:00")
        with patch.object(monitor,"fetch_company",side_effect=ValueError("markup changed")):
            state=monitor.update({"companies":[K]},state,"2026-11-15T22:00:00+00:00")
        self.assertTrue(state["jobs"][j["key"]]["active"])
        self.assertEqual(state["sources"][K["name"]]["status"],"error")

    def test_manual_targets_are_not_claimed_as_automated(self):
        page=(ROOT/"docs/index.html").read_text(encoding="utf-8")
        for name in ["Fraunhofer IWS","Material Engineering Center Saarland","GKN Powder Metallurgy","Schmitz-Metallographie"]:
            self.assertIn(name,page)
        names={c["name"] for c in CFG["companies"]}
        self.assertEqual(len(CFG["companies"]),len(names))
        self.assertNotIn("Material Engineering Center Saarland",names)

if __name__=="__main__":unittest.main()
