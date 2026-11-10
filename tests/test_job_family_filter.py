"""Regression tests for preference-based job-family exclusion."""
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor
import notify

class JobFamilyTests(unittest.TestCase):
    def test_excludes_unrelated_titles(self):
        examples = [
            'HR Business Partner (m/w/d)', 'Talent Acquisition Specialist (f/m/d)',
            'Recruiting Manager', 'Student - Chemical Engineering',
            'Senior Finance Manager (all genders)', 'Head of Accounting & Tax',
            'Financial Controller', 'Procurement Specialist',
            'Strategischer Einkäufer (m/w/d)', 'Purchasing Manager',
            'Sales Director - Scientific Instruments', 'Account Executive, Materials & Industrial',
            'Business Development Manager', 'Marketing Communications Manager',
            'Team Assistant', 'Executive Assistant', 'Software Engineer',
            'Initiativbewerbung', 'Working Student Lab Research'
        ]
        for title in examples:
            with self.subTest(title=title):
                self.assertTrue(monitor.qualification_preference({'title':title})['hide_by_default'])

    def test_keeps_relevant_technical_titles(self):
        examples = [
            'Application Scientist - Particle Analysis',
            'R&D Engineer Polymer Materials', 'Materials Scientist',
            'SEM Technician (f/m/d)', 'Process Engineer',
            'Produktionschemiker/-in (m/w/d)',
            'Formulierungsentwickler (m/w/d)',
            'Analytical Method Development Scientist',
            'Research Associate Analytical Chemistry',
            'Chemikerin Prozessentwicklung',
        ]
        for title in examples:
            with self.subTest(title=title):
                self.assertFalse(monitor.qualification_preference({'title':title})['hide_by_default'])

    def test_description_does_not_exclude_technical_job(self):
        j={'title':'Process Development Engineer',
           'description':'Coordinate with procurement, finance, HR, recruiting and accounting teams'}
        self.assertFalse(monitor.qualification_preference(j)['hide_by_default'])

    def test_exclusions_never_trigger_alert(self):
        j={'key':'recruit','company':'Example','title':'HR Materials Recruiter','description':'silica FTIR nanoparticles formulation',
           'location':'Munich','url':'https://example.com/recruit'}
        cfg={'companies':[{'name':'Example','platform':'personio','slug':'example','careers_url':'https://example.jobs.personio.com'}]}
        with patch.object(monitor,'fetch_company',return_value=[j]):
            state=monitor.update(cfg,{'jobs':{},'sources':{}},'2026-11-10T13:00:00+00:00')
        result=state['jobs']['recruit']
        self.assertEqual(result['match_band'],'Not target')
        self.assertTrue(result['hide_by_default'])
        result['at_startup']=False
        state['alerts_started_at']='2026-11-10T12:00:00+00:00'
        self.assertEqual(notify.candidates(state),[])

    def test_mixed_country_locations_require_verification(self):
        self.assertEqual(monitor.location_status({'location':'Munich, Pilsen'}),'verify_location')
        self.assertEqual(monitor.location_status({'location':'Karlsfeld (Munich)'}),'germany')
        self.assertEqual(monitor.location_status({'location':'Shanghai, China'}),'outside')

if __name__=='__main__':
    unittest.main()
