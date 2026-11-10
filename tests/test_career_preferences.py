import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

RUDOLF = {'name':'RUDOLF','slug':'rudolf','platform':'personio','careers_url':'https://rudolf.jobs.personio.de'}

class PreferenceTests(unittest.TestCase):
    def test_training_hidden(self):
        examples = ['Ausbildung zum Chemielaborant (m/w/d)',
                    'Auszubildende im Beruf Pharmakant',
                    'Schülerpraktikum (m/w/d)',
                    'Working Student Battery Testing',
                    'Werkstudentin Forschung',
                    'Dualer Student']
        for title in examples:
            with self.subTest(title=title):
                self.assertTrue(monitor.qualification_preference({'title':title})['hide_by_default'])
    def test_vocational_titles_hidden_without_excluding_chemists(self):
        self.assertTrue(monitor.qualification_preference({'title':'Chemielaboranten (m/w/d)'})['hide_by_default'])
        self.assertTrue(monitor.qualification_preference({'title':'Produktionsmitarbeiter Chemie'})['hide_by_default'])
        self.assertFalse(monitor.qualification_preference({'title':'Produktionschemiker/-in (m/w/d)'})['hide_by_default'])
        self.assertFalse(monitor.qualification_preference({'title':'Scientist Materials Research'})['hide_by_default'])
        self.assertFalse(monitor.qualification_preference({'title':'SEM Technician (f/m/d)'})['hide_by_default'])
    def test_location_recipharm(self):
        self.assertEqual(monitor.location_status({'location':'Zwickau'}),'germany')
        self.assertEqual(monitor.location_status({'location':'Monheim am Rhein'}),'germany')
    def test_source_page_html_links(self):
        html='''<html><body><a href="/job/1696535?language=de"><h3>Initiativbewerbung (Festanstellung)</h3><span>Geretsried</span></a>
        <a href="https://rudolf.jobs.personio.de/job/2277532?language=de"><h3>Produktionschemiker/-in (m/w/d)</h3></a>
        <a href="https://not-rudolf.example/job/999">Irrelevant</a></body></html>'''
        jobs=monitor.parse_personio_html(RUDOLF,html)
        self.assertEqual(len(jobs),2)
        self.assertEqual(jobs[1]['title'],'Produktionschemiker/-in (m/w/d)')
        self.assertEqual(jobs[1]['source_mode'],'html_fallback')
        self.assertEqual(jobs[1]['key'],'personio:rudolf:2277532')
        self.assertEqual(jobs[0]['location'],'')
    def test_empty_or_unparseable_html_is_error_not_zero(self):
        with self.assertRaises(ValueError):
            monitor.parse_personio_html(RUDOLF,'<html><body>0 jobs</body></html>')
    def test_xml_404_falls_back_to_career_page(self):
        html='<a href="/job/2277532"><h3>Produktionschemiker/-in</h3></a>'
        err=HTTPError('https://rudolf.jobs.personio.de/xml?language=de',404,'Not Found',{},None)
        with patch.object(monitor,'get_xml',side_effect=err),patch.object(monitor,'get_html',return_value=html) as getter:
            jobs=monitor.fetch_company(RUDOLF)
        self.assertEqual(len(jobs),1)
        getter.assert_called_once_with(RUDOLF['careers_url'])
    def test_forbidden_xml_not_bypassed(self):
        err=HTTPError('https://rudolf.jobs.personio.de/xml?language=de',403,'Forbidden',{},None)
        with patch.object(monitor,'get_xml',side_effect=err),patch.object(monitor,'get_html') as getter:
            with self.assertRaises(HTTPError):
                monitor.fetch_company(RUDOLF)
        getter.assert_not_called()
    def test_excluded_label_not_high_priority(self):
        config={'companies':[{'name':'Example','slug':'example','platform':'ashby','careers_url':'https://example.com'}]}
        jobs=[{'key':'one','company':'Example','title':'Ausbildung zum Chemielaborant','description':'Nanoparticles silica formulation FTIR',
               'location':'Munich','url':'https://example.com/1'}]
        with patch.object(monitor,'fetch_company',return_value=jobs):
            state=monitor.update(config,{'jobs':{},'sources':{}},'2026-11-10T14:00:00+00:00')
        self.assertTrue(state['jobs']['one']['hide_by_default'])
        self.assertEqual(state['jobs']['one']['match_band'],'Not target')

if __name__=='__main__':
    unittest.main()
