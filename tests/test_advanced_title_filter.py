"""Preference exclusions for training/theses and unrelated mechanical occupations.

All checks operate on job titles, not body text. Hidden roles stay stored
and remain visible if the user turns off the preference filter.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor
import notify


class AdvancedTitleFilterTests(unittest.TestCase):
    def test_hide_student_training_and_thesis_titles(self):
        titles = [
            'Masterarbeit – Oberflächenfunktionalisierung von SiO2',
            'Bachelorarbeit: Polymer Research',
            'Master Thesis: Nanoparticles',
            "Master's Thesis – Particle Characterization",
            'M.Sc. Thesis – Lab Research',
            'Thesis in Materials Characterization',
            'Abschlussarbeit im Bereich Chemie',
            'Studienarbeit zur Sol-Gel-Synthese',
            'Diplomarbeit Polymerchemie',
            'Masterand (m/w/d) Prozessentwicklung',
            'Bachelorandin in der Materialforschung',
            'Forschungspraktikum (m/w/d) Sol-Gel',
            'Pflichtpraktikum Materialentwicklung',
            'Praktikant/in in der F&E',
            'Praxissemester – Materialwissenschaft',
            'Studentische Hilfskraft Chemie',
            'Doctoral Researcher – Colloidal Nanoparticles',
        ]
        for title in titles:
            with self.subTest(title=title):
                result = monitor.qualification_preference({'title': title})
                self.assertTrue(result['hide_by_default'], title)
                self.assertEqual(result['career_track'], 'training', title)

    def test_hide_mechanical_design_occupations(self):
        titles = [
            'Mechanical Engineer (m/f/d)',
            'Senior Mechanical Design Engineer',
            'Lead Mechanical Development Engineer – Polymer Equipment',
            'Mechanical Systems Engineer',
            'Engineer Mechanical Design (m/f/d)',
            'Maschinenbauingenieur (m/w/d)',
            'Entwicklungsingenieur Maschinenbau',
            'Konstruktionsingenieur (m/w/d)',
            'Mechatronics Engineer',
            'CAD Designer (m/f/d)',
        ]
        for title in titles:
            with self.subTest(title=title):
                result = monitor.qualification_preference({'title': title})
                self.assertTrue(result['hide_by_default'], title)
                self.assertEqual(result['career_track'], 'unrelated', title)

    def test_preserve_chemistry_materials_and_professional_roles(self):
        titles = [
            'Materials Scientist – Mechanical Properties Testing',
            'Mechanical Testing Engineer – Polymer Materials',
            'R&D Scientist – Ceramic Mechanical Characterization',
            'Process Engineer – Chemical Plant',
            'Research Scientist – Sol-Gel Materials',
            'Production Chemist (m/f/d)',
            'Formulation Development Engineer',
            'Chemical Mechanical Polishing Process Engineer',
            'Materials Engineer – Surface Modification',
            'Research Associate – Particle Characterization',
            'Postdoctoral Researcher – Nanoparticle Synthesis',
            'Chemiker (m/w/d) Produktentwicklung',
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(monitor.qualification_preference({'title': title})['hide_by_default'], title)

    def test_unrelated_terms_in_description_do_not_hide_technical_role(self):
        job = {'title': 'Materials Development Engineer',
               'description': 'Collaborates with mechanical engineers and supervises a master thesis.'}
        self.assertFalse(monitor.qualification_preference(job)['hide_by_default'])

    def test_excluded_jobs_have_not_target_priority_and_no_alert(self):
        job = {'key': 'example:1', 'company': 'Example', 'title': 'Master Thesis – Silica Nanoparticles',
               'description': 'DoE, sol-gel, colloids, FTIR, materials development.',
               'location': 'Munich, Germany', 'url': 'https://example.org/jobs/1'}
        conf = {'companies': [{'name': 'Example', 'platform': 'personio',
                               'slug': 'example', 'careers_url': 'https://example.org/jobs'}]}
        with patch.object(monitor, 'fetch_company', return_value=[job]):
            state = monitor.update(conf, {'jobs': {}, 'sources': {}}, '2026-11-12T16:00:00+00:00')
        new_job = state['jobs']['example:1']
        self.assertTrue(new_job['active'])  # remains stored
        self.assertTrue(new_job['hide_by_default'])
        self.assertEqual(new_job['match_band'], 'Not target')
        new_job['at_startup'] = False
        state['alerts_started_at'] = '2026-11-12T12:00:00+00:00'
        self.assertEqual(notify.candidates(state), [])


if __name__ == '__main__':
    unittest.main()
