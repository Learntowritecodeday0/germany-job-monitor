import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qualification_priority import priority_review


def job(title, description, **extras):
    x = {'title': title, 'description': description, 'source_mode': 'structured_feed',
         'match_band': 'Review first', 'worksite_city':'Alzenau',
         'worksite_state': 'Bayern', 'worksite_country': 'Germany'}
    x.update(extras)
    return x


class QualificationPriorityTests(unittest.TestCase):
    def test_battery_sector_preferred_electrochemical_testing_learnable(self):
        description = (
          'Your Day-to-Day: Plan compounding trials, DoE and scale-up. '
          'Your Profile: Master degree in materials science. '
          'Professional background in battery or energy storage industry preferable '
          'Analytical mindset: Experience with statistical data analysis, '
          'Design of Experiments (DoE) and ideally Bayesian optimization. '
          'Experience with electrochemical testing and evaluation – or the openness '
          'and curiosity to learn these skills with us. '
          'Experience with project management – or the willingness to learn them. '
          'Why us: teamwork is key.')
        review = priority_review(job('Battery Material Compounds Developer', description))['qualification_priority']
        self.assertEqual(review['status'], 'parsed')
        self.assertIn('Battery-sector experience', [x['name'] for x in review['preferred']])
        self.assertIn('Electrochemical testing / characterization', [x['name'] for x in review['learnable']])
        self.assertIn('DoE / experimental design', [x['name'] for x in review['listed']])
        self.assertNotIn('DoE / experimental design', [x['name'] for x in review['preferred']])

    def test_sem_required_vs_desirable_distinction(self):
        desc = ('Your Role: SEM inspection is essential to the project. '
                'What You Bring: - Previous hands-on experience operating SEM systems '
                '- Experience with FIB and EDX is highly desirable '
                '- Technical documentation is required '
                '- Previous experience working in a semiconductor cleanroom is an advantage '
                'Our work culture: Teamwork, project management, and communication.')
        p=priority_review(job('SEM Technician',desc))['qualification_priority']
        self.assertIn('SEM microscopy',[x['name'] for x in p['listed']])
        self.assertIn('Focused ion beam (FIB)',[x['name'] for x in p['preferred']])
        self.assertIn('EDS / EDX elemental analysis',[x['name'] for x in p['preferred']])
        self.assertIn('Technical documentation / SOPs',[x['name'] for x in p['explicit']])
        self.assertNotIn('Cross-team collaboration',[x['name'] for x in p['listed']])

    def test_explicit_aerospace_years_not_softened_by_ideally_two_programs(self):
        desc=('Your Day-to-Day: Manufacture and test aerospace materials. '
              'Your Profile: - Minimum of 8-10 years of experience in aerospace '
              'materials and processes engineering in at least one aircraft development '
              'program, ideally two programs. '
              '- Ideally experience in test specification and material testing.')
        p=priority_review(job('Senior Structures Materials & Processes Engineer',desc))['qualification_priority']
        self.assertEqual(p['status'],'parsed')
        self.assertEqual(len(p['experience_flags']),1)
        self.assertIn('Minimum of 8-10 years',p['experience_flags'][0]['text'])

    def test_explicit_and_preferred_bilingual_keywords(self):
        desc=('Ihre Aufgaben: Durchführung von Versuchsreihen. '
              'Ihr Profil: - FTIR ist erforderlich '
              '- DLS wünschenswert '
              '- Mindestens 5 Jahre Erfahrung in der Materialentwicklung '
              '- Erfahrung mit der Sol-Gel-Synthese von Vorteil.')
        p=priority_review(job('Entwickler Werkstoffe',desc))['qualification_priority']
        self.assertIn('FTIR',[x['name'] for x in p['explicit']])
        self.assertIn('DLS / zeta potential',[x['name'] for x in p['preferred']])
        self.assertIn('Sol-gel synthesis',[x['name'] for x in p['preferred']])
        self.assertEqual(len(p['experience_flags']),1)

    def test_qualification_unknown_without_profile_heading(self):
        p=priority_review(job('Research Scientist','Develop silica materials and study FTIR and SEM in the lab. '*6))['qualification_priority']
        self.assertEqual(p['status'],'unavailable')
        self.assertFalse(p['explicit'])

    def test_title_only_stays_unknown(self):
        p=priority_review(job('SEM Technician','',source_mode='html_fallback'))['qualification_priority']
        self.assertEqual(p['status'],'unavailable')

    def test_task_section_does_not_make_a_method_mandatory(self):
        desc=('Your Tasks: Must perform SEM, FIB and DoE every day. '
              'Your Profile: Experience with FTIR is a plus. Applicants work in an industrial analytical lab with several instruments and perform routine quality checks.')
        p=priority_review(job('Materials Scientist',desc))['qualification_priority']
        self.assertEqual(p['explicit'],[])
        self.assertIn('FTIR',[x['name'] for x in p['preferred']])
        self.assertNotIn('SEM microscopy',[x['name'] for x in p['listed']])

    def test_fields_never_mutate_priorities_or_location(self):
        original=job('SEM Technician','Your Tasks: Use SEM and EDX. Your Profile: Previous experience with SEM. '
                     'FIB experience is highly desirable.')
        before=original.copy()
        original.update(priority_review(original))
        for f in ['match_band','worksite_city','worksite_state','worksite_country']:
            self.assertEqual(before[f],original[f])


if __name__=='__main__':unittest.main()
