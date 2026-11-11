"""Conservative eligibility and worksite flags without personal information."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import screening
import notify


def make_job(description='', **kwargs):
    return {'key': 'job1', 'title': 'Materials Scientist', 'description': description,
            'active': True, 'at_startup': False, 'match_band': 'Review first',
            'location_status': 'germany', 'hide_by_default': False,
            'first_detected': '2026-11-11T11:00:00+00:00', **kwargs}


class ScreeningTests(unittest.TestCase):
    def test_explicit_nationality_requirements_are_flagged(self):
        examples = [
            'Applicants must have EU citizenship to be eligible.',
            'NATO nationality is required for this position.',
            'Only German citizens are eligible.',
            'US-person status required due to export regulation.',
            'EU citizenship is mandatory.',
            'Only citizens of NATO member states can apply.',
            'Only nationals of EPO member states can apply.',
        ]
        for text in examples:
            with self.subTest(text=text):
                flags = screening.screening_notes(make_job(text))
                self.assertTrue(flags['citizenship_restriction_detected'])

    def test_generic_equality_or_export_language_not_citizenship_requirement(self):
        examples = [
            'We welcome everyone regardless of nationality or citizenship.',
            'EU research program funded this project.',
            'Knowledge of ITAR or export controls is desirable.',
            'An international applicant can join our team.',
            'We support NATO-related engineering research.',
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertFalse(screening.screening_notes(make_job(text))['citizenship_restriction_detected'])

    def test_clearance_and_export_not_equivalent_to_nationality_restriction(self):
        s = screening.screening_notes(make_job('ITAR compliance and security clearance required.'))
        self.assertFalse(s['citizenship_restriction_detected'])
        self.assertTrue(any('Export-control' in flag for flag in s['screening_flags']))
        self.assertTrue(any('Security clearance' in flag for flag in s['screening_flags']))

    def test_work_authorization_and_location_review(self):
        s = screening.screening_notes(make_job('Must already have unrestricted right to work in Germany.', location_status='verify_location'))
        self.assertTrue(any('Work authorization' in x for x in s['screening_flags']))
        self.assertTrue(any('Worksite' in x for x in s['screening_flags']))

    def test_specialized_seniority_flag_not_exclusion(self):
        s = screening.screening_notes(make_job('Minimum 8 years of experience in aerospace materials and aircraft programs.'))
        self.assertTrue(any('Specialized' in x for x in s['screening_flags']))
        self.assertNotIn('hide_by_default', s)

    def test_title_only_flag(self):
        s = screening.screening_notes(make_job('', source_mode='html_fallback'))
        self.assertTrue(any('Title-only' in x for x in s['screening_flags']))

    def test_suppresses_explicit_restriction_alerts_without_affecting_existing_jobs(self):
        j1=make_job('Only German citizens are eligible.')
        j1.update(screening.screening_notes(j1))
        j2=make_job('Formulation development', key='job2')
        j2.update(screening.screening_notes(j2))
        state={'jobs':{'job1':j1,'job2':j2},'alerts_started_at':'2026-11-11T10:00:00+00:00','alerts_sent':{}}
        self.assertEqual([j['key'] for j in notify.candidates(state)],['job2'])

    def test_public_output_contains_no_private_profile_data(self):
        j=make_job('EU citizenship mandatory.')
        data=screening.screening_notes(j)
        self.assertNotIn('applicant_nationality',str(data))
        self.assertNotIn('chancenkarte',str(data).lower())

if __name__=='__main__':
    unittest.main()
