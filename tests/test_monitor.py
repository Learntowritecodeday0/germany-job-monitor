import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

class MonitorTests(unittest.TestCase):
    def test_text_stripping(self):
        self.assertEqual(monitor.plain_text('<p>Silica <b>nanoparticles</b></p>'), 'Silica nanoparticles')
    def test_ashby_normalization(self):
        job = monitor.normalize_ashby({'name':'Test','slug':'test','careers_url':'https://example.com'}, {'title':'R&D Engineer','location':'Munich','jobUrl':'https://example.com/job','descriptionPlain':'nanoparticle formulation','address':{'postalAddress':{'addressCountry':'DE'}}})
        self.assertEqual(monitor.location_status(job),'germany')
        self.assertEqual(monitor.triage(job)['match_band'],'Possible')
    def test_foreign_location(self):
        self.assertEqual(monitor.location_status({'location':'Fort Collins, Colorado, USA','country':'US'}),'outside')
    def test_unknown_location_visible_for_review(self):
        self.assertEqual(monitor.location_status({'location':'Hybrid','country':''}),'verify_location')
    def test_not_student_roles(self):
        self.assertEqual(monitor.triage({'title':'Working Student - Nanoparticles', 'description':'DLS and surface chemistry'})['match_band'],'Not target')
    def test_first_check_is_baseline(self):
        config={'companies':[{'name':'Example','slug':'example','platform':'ashby','careers_url':'https://example.com'}]}
        mock_jobs=[{'key':'example:1','company':'Example','title':'Nanoparticle Scientist','location':'Berlin, Germany','description':'silica formulation DLS','country':'DE','url':'https://example.com/1'}]
        with patch.object(monitor,'fetch_company',return_value=mock_jobs):
            state=monitor.update(config, {'jobs':{},'sources':{}},'2026-11-10T10:00:00+00:00')
            self.assertTrue(state['jobs']['example:1']['at_startup'])
            state=monitor.update(config,state,'2026-11-10T14:00:00+00:00')
            self.assertEqual(state['jobs']['example:1']['first_detected'],'2026-11-10T10:00:00+00:00')
    def test_source_failure_keeps_existing_jobs(self):
        config={'companies':[{'name':'Example','slug':'example','platform':'ashby','careers_url':'https://example.com'}]}
        state={'jobs':{'x':{'key':'x','company':'Example','active':True,'first_detected':'2026-11-10'}},'sources':{'Example':{'initialized':True}}}
        with patch.object(monitor,'fetch_company',side_effect=ValueError('Temporary failure')):
            new=monitor.update(config,state,'2026-11-10T14:00:00+00:00')
        self.assertTrue(new['jobs']['x']['active'])
        self.assertEqual(new['sources']['Example']['status'],'error')

if __name__=='__main__':unittest.main()
