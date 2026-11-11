import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import competency_review as cr
import monitor
import notify


def job(title, desc, **extra):
    x={'title':title,'description':desc,'hide_by_default':False,'source_mode':'structured_feed',
       'match_band':'Possible','company':'Example','location':'Munich','key':'id',
       'url':'https://example.org/jobs/1','at_startup':False,'active':True,
       'first_detected':'2026-11-11T10:00:00+00:00'}
    x.update(extra)
    return x

class CompetencyReviewTests(unittest.TestCase):
    def test_categories_count_recognised_items_and_documented_overlap(self):
        x=cr.competency_review(job('Silica Formulation Chemist',
            'Your Tasks: Develop silica nanoparticle formulations by DoE and DLS testing. '
            'Your Profile: Teamwork, communication skills and GMP validation experience.'))['competency_counts']
        self.assertEqual((x['technical']['matched'],x['technical']['total']),(2,2))
        self.assertEqual((x['method']['matched'],x['method']['total']),(2,2))
        self.assertEqual((x['general']['matched'],x['general']['total']),(2,3))
        self.assertIn('Formal ISO / GMP / medical-device validation',x['general']['verify'])

    def test_battery_role_has_distinct_sector_gap(self):
        x=cr.competency_review(job('Battery Material Compounds Developer',
            'Your Day-to-Day: Optimize battery slurries with DoE and lab scale-up. '
            'Your Profile: Battery electrochemistry, project management and English skills.'))['competency_counts']
        self.assertEqual((x['technical']['matched'],x['technical']['total']),(0,1))
        self.assertEqual((x['method']['matched'],x['method']['total']),(2,2))
        self.assertEqual((x['general']['matched'],x['general']['total']),(1,1))

    def test_edx_not_misclassified_as_dispersion(self):
        x=cr.competency_review(job('SEM Technician',
            'Your Tasks: Perform scanning electron microscopy and Energy-Dispersive X-ray Spectroscopy on thin films. '
            'Your Profile: SOP documentation.'))['competency_counts']
        self.assertEqual((x['technical']['matched'],x['technical']['total']),(0,0))
        self.assertEqual((x['method']['matched'],x['method']['total']),(1,1))

    def test_no_general_from_benefits_boilerplate(self):
        x=cr.competency_review(job('Silica Scientist',
            'Your Mission: Synthesize silica nanoparticles and use DoE for experiments. '
            'Your Profile: PhD in chemistry. Why us: great teamwork, project management, and communication perks.'))['competency_counts']
        self.assertEqual(x['general']['total'],0)

    def test_html_headings_without_colons_are_understood(self):
        x=cr.competency_review(job('Silica Scientist',
            '<h2>Your Tasks</h2><p>Perform silica synthesis using FTIR.</p><h2>Your Profile</h2>'
            '<p>Cross-functional teamwork and project management.</p><h2>Benefits</h2>'
            '<p>GMP validation equipment used by other colleagues.</p>'))['competency_counts']
        self.assertEqual(x['general']['total'],2)
        self.assertEqual(x['general']['matched'],2)

    def test_unknown_does_not_become_false_zero(self):
        self.assertIsNone(cr.competency_review(job('Research Engineer','Short description'))['competency_counts'])

    def test_python_sdk_and_electric_motors_hidden(self):
        for title in ['Senior Python SDK Engineer (m/f/d)',
                      'Process Engineer Electric Motors for Robotics (m/f/x)',
                      'SDK Integration Engineer']:
            with self.subTest(title=title):
                pref=monitor.qualification_preference({'title':title})
                self.assertTrue(pref['hide_by_default'])
                hidden=job(title,'Your Tasks: Apply DoE to optimize nanoparticle synthesis.',
                           hide_by_default=True,match_band='Not target')
                self.assertEqual(notify.candidates({'jobs':{'id':hidden}}),[])

    def test_chemistry_roles_not_hidden_by_vague_engineering_words(self):
        for title in ['Process Engineer Silica Sol-Gel',
                      'Application Scientist - Particle Analysis',
                      'Research Scientist Polymer Materials for Robotics',
                      'Materials Scientist', 'SEM Technician (f/m/d)',
                      'Materials Scientist - Insulation Coatings for Electric Motors']:
            with self.subTest(title=title):
                self.assertFalse(monitor.qualification_preference({'title':title})['hide_by_default'])

    def test_legacy_priority_and_location_not_rewritten(self):
        original=job('Nanoparticle Chemist','Your tasks: Prepare silica particles by DoE and filtration.',
                     match_band='Review first',worksite_city='Alzenau',worksite_state='Bayern',worksite_country='Germany')
        before=dict(original)
        original.update(cr.competency_review(original))
        for field in ['match_band','worksite_city','worksite_state','worksite_country']:
            self.assertEqual(original[field],before[field])

if __name__=='__main__': unittest.main()
