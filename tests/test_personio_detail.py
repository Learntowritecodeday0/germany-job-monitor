"""Offline regression tests for enriching two Personio title-only employers."""
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

COMPANY = {"name":"RUDOLF", "platform":"personio", "slug":"rudolf", "careers_url":"https://rudolf.jobs.personio.de"}
SAMPLE = {
    "key":"personio:rudolf:2805325",
    "company":"RUDOLF",
    "title":"Produktionschemiker/-in (m/w/d)",
    "description":"", "country":"", "location":"",
    "url":"https://rudolf.jobs.personio.de/job/2805325",
    "published_at":None, "source_mode":"html_fallback",
}

RUDOLF_PAGE = '''<html><head><title>Jobs bei RUDOLF</title></head><body>
<main><h1>Produktionschemiker/-in (m/w/d)</h1><div>Geretsried, Deutschland</div><p>Vollzeit</p>
<h2>Ihre Aufgaben</h2><ul>
<li>Optimierung und Weiterentwicklung chemischer Herstellprozesse in enger Zusammenarbeit mit Entwicklung und Produktion</li>
<li>Scale-up und Überführung neuer Verfahren in den Produktionsmaßstab</li></ul>
<h2>Ihr Profil</h2><ul><li>Studium Chemie oder Verfahrenstechnik; Erfahrung mit Prozessoptimierung und Scale-up</li></ul>
<h2>Warum wir?</h2><p>Viele spannende gemeinsame Events und Karrierechancen.</p>
<h2>Über uns</h2><p>Das Unternehmen hat viele Büros in aller Welt.</p></main></body></html>'''

NVISION = {**SAMPLE, "company":"NVision Quantum Technologies", "title":"Senior Research Engineer (m/f/d)",
          "url":"https://nvision-quantum-technologies.jobs.personio.com/job/2838499",
          "key":"personio:nvision-quantum-technologies:2838499"}
NVISION_PAGE = '''<html><head><script type="application/ld+json">{
"@context":"https://schema.org","@type":"JobPosting",
"title":"Senior Research Engineer (m/f/d)",
"description":"<p>Develop complete scientific instruments and prototypes from initial design through assembly and testing.</p><p>Experience with fluidic systems and automation is required for multidisciplinary systems.</p>",
"jobLocation":{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":"Ulm","addressCountry":"DE"}},
"datePosted":"2026-11-03"}</script></head><body><main><h1>Senior Research Engineer (m/f/d)</h1></main></body></html>'''

class PersonioDetailTests(unittest.TestCase):
    def test_visible_semantic_sections_and_worksite(self):
        job = monitor.enrich_personio_fallback_job(SAMPLE, RUDOLF_PAGE)
        self.assertEqual(job['source_mode'],'html_detail')
        self.assertIn('Prozessoptimierung', job['description'])
        self.assertNotIn('gemeinsame Events',job['description'])
        self.assertEqual(job['location'],'Geretsried, Deutschland')
        self.assertEqual(monitor.location_status(job),'germany')
        self.assertIsNone(job['published_at'])

    def test_jsonld_jobposting_detail(self):
        job=monitor.enrich_personio_fallback_job(NVISION, NVISION_PAGE)
        self.assertEqual(job['source_mode'],'html_detail')
        self.assertEqual(job['location'],'Ulm, DE')
        self.assertEqual(job['country'],'DE')
        self.assertIn('fluidic systems',job['description'])
        self.assertEqual(job['published_at'],'2026-11-03')

    def test_no_description_remains_title_only(self):
        job=monitor.enrich_personio_fallback_job(SAMPLE,'<html><body><h1>Produktionschemiker/-in (m/w/d)</h1><div>Geretsried, Deutschland</div></body></html>')
        self.assertEqual(job['source_mode'],'html_fallback')
        self.assertFalse(job['description'])

    def test_mismatched_job_title_not_accepted(self):
        job=monitor.enrich_personio_fallback_job(SAMPLE,NVISION_PAGE)
        self.assertEqual(job,SAMPLE)

    def test_failed_detail_page_preserves_title_only(self):
        from urllib.error import HTTPError
        bad=HTTPError(SAMPLE['url'],404,'Not found',{},None)
        with patch.object(monitor,'get_html',side_effect=bad):
            self.assertEqual(monitor.enrich_personio_fallback([dict(SAMPLE)]),[SAMPLE])

    def test_status_reports_partial_details(self):
        with patch.object(monitor,'fetch_company',return_value=[dict(SAMPLE)]),patch.object(monitor,'get_html',return_value=RUDOLF_PAGE):
            result=monitor.update({'companies':[COMPANY]},{'jobs':{},'sources':{}},'2026-11-11T12:00:00Z')
        status=result['sources']['RUDOLF']
        self.assertEqual(status['details_extracted'],1)
        self.assertEqual(status['title_only_count'],0)
        self.assertEqual(status['source_mode'],'html_detail')
        self.assertEqual(result['jobs'][SAMPLE['key']]['source_mode'],'html_detail')

if __name__ == '__main__':
    unittest.main()
