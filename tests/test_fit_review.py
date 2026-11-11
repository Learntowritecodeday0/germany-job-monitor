import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fit_review


def job(title, description, **kw):
    data = dict(title=title, description=description, location='Munich',
                location_status='germany', match_band='Review first',
                active=True, hide_by_default=False, screening_flags=[],
                published_at='2026-11-01', first_detected='2026-11-10')
    data.update(kw)
    return data


class EvidenceReviewTests(unittest.TestCase):
    def test_material_formulation_and_doe_overlap(self):
        a = fit_review.review_job(job('Developer – Battery Material Compounds',
            'Your Mission: Optimize formulations of material compounds with DoE experiments. '
            'Your Profile: Chemistry or materials science degree. Battery electrochemistry desirable. '
            'Why us: Benefits and rewards.'))
        self.assertIn('Formulation / dispersion work', a['method_overlap'])
        self.assertIn('DoE / experimental design', a['method_overlap'])
        self.assertTrue(any('Battery electrochemistry' in x for x in a['technical_gaps_to_verify']))
        self.assertTrue(a['technical_review'].startswith('Multiple'))

    def test_aerospace_industry_not_equivalent_to_materials_research(self):
        a = fit_review.review_job(job('Senior Structures Materials & Processes Engineer',
            'Your Profile: Minimum 8-10 years of experience in aerospace materials and processes '
            'engineering, including at least one aircraft development program. Why us: Great team.'))
        self.assertIn('Aircraft development / aerospace certification', a['technical_gaps_to_verify'])
        self.assertIn('Sector-specific years of experience', a['technical_gaps_to_verify'])
        self.assertNotEqual(a['technical_review'], 'Multiple method overlaps')

    def test_sem_edx_not_mistaken_for_dispersion_formulation(self):
        a = fit_review.review_job(job('SEM Technician',
            'Your Role: Perform Scanning Electron Microscopy and Energy-Dispersive X-ray Spectroscopy (EDX). '
            'What You Bring: Hands-on SEM experience and electron microscopy sample preparation.'))
        self.assertIn('Materials characterization', a['method_overlap'])
        self.assertNotIn('Formulation / dispersion work', a['method_overlap'])
        self.assertEqual(a['technical_review'], 'Some method overlap')

    def test_real_dispersion_work_still_matches(self):
        a = fit_review.review_job(job('Formulation Scientist',
            'Your tasks: Develop stable aqueous dispersions and emulsion formulations with surfactants. '
            'Your Profile: Experience with colloid chemistry.'))
        self.assertIn('Formulation / dispersion work', a['method_overlap'])

    def test_composite_winding_is_flagged_as_separate_domain(self):
        a = fit_review.review_job(job('R&D Engineer – Composite Winding Process',
            'Your tasks: Use DoE for winding process optimization. '
            'Your Profile: Experience with filament winding, composite winding and pre-preg layup required.'))
        self.assertIn('DoE / experimental design', a['method_overlap'])
        self.assertIn('Composite winding / layup processes', a['technical_gaps_to_verify'])

    def test_sem_method_vs_instrument_design(self):
        a=fit_review.review_job(job('SEM Technician',
            'Your tasks: Conduct SEM analysis and sample preparation to evaluate microstructure and surface properties across experimental material samples. Your Profile: Degree in chemistry or materials science and practical microscopy experience.'))
        self.assertIn('Materials characterization', a['method_overlap'])
        self.assertFalse(a['technical_gaps_to_verify'])
        b=fit_review.review_job(job('Senior Research Engineer',
            'Your mission: Prototype complete scientific instrumentation and integrate components in the laboratory. Your Profile: 4+ years building scientific instruments and complex fluidic systems; proven integration experience.'))
        self.assertTrue(any('instrument construction' in x for x in b['technical_gaps_to_verify']))
        self.assertEqual(b['technical_review'], 'Limited documented overlap')

    def test_lacquer_film_not_claimed_direct(self):
        a=fit_review.review_job(job('Lacquer Development Engineer',
            'Your tasks: Develop lacquer films and characterize resistance and adhesion. Your Profile: Must have hands-on electron-beam curing of industrial coatings and paint film adhesion tests with verified manufacturing experience.'))
        self.assertFalse(any('Industrial film coatings' == x for x in a['method_overlap']))
        self.assertIn('Industrial lacquer curing / film testing', a['technical_gaps_to_verify'])

    def test_title_only_does_not_invent_criteria(self):
        a=fit_review.review_job(job('Senior Research Engineer', '', source_mode='html_fallback'))
        self.assertEqual(a['technical_review'],'Insufficient job details')
        self.assertFalse(a['method_overlap'])
        self.assertFalse(a['technical_gaps_to_verify'])

    def test_hidden_unrelated_role_is_not_promoted_by_company_marketing(self):
        a=fit_review.review_job(job('Head of Procurement',
            'We research nanoparticles and polymers for aerospace applications.', hide_by_default=True))
        self.assertEqual(a['technical_review'], 'Outside preferred job families')
        self.assertFalse(a['method_overlap'])

    def test_location_tiers_do_not_infer_company_hq(self):
        self.assertEqual(fit_review.worksite_preference(job('Materials Scientist','ok', location='Martinsried, Germany')), 'Munich region')
        self.assertEqual(fit_review.worksite_preference(job('Materials Scientist','ok', location='Alzenau, Germany')), 'Southern Germany')
        self.assertEqual(fit_review.worksite_preference(job('Materials Scientist','ok', location='Zwickau, Germany')), 'Elsewhere Germany')
        self.assertEqual(fit_review.worksite_preference(job('Materials Scientist','ok', location='', location_status='verify_location')), 'Worksite unverified')
        self.assertEqual(fit_review.worksite_preference(job('Materials Scientist','ok', location='Munich; Delft', location_status='verify_location')), 'Worksite unverified')

    def test_prior_fields_and_alert_state_remain_untouched(self):
        j = job('SiO2 Research Scientist', 'Your profile: sol-gel silica synthesis.',
                citizenship_restriction_detected=True, at_startup=True, alerts_sent='old')
        state={'jobs':{'1':j},'alerts_started_at':'2026-11-10','alerts_sent':{'key':'date'},'sources':{'x':{}},'schema':1}
        fit_review.review_state(state)
        self.assertEqual(state['jobs']['1']['match_band'],'Review first')
        self.assertTrue(state['jobs']['1']['citizenship_restriction_detected'])
        self.assertEqual(state['alerts_sent'],{'key':'date'})
        self.assertEqual(state['jobs']['1']['published_at'],'2026-11-01')
        self.assertNotIn('applicant_nationality',state['jobs']['1'])
        self.assertNotIn('residence_permit',state['jobs']['1'])

    def test_specialist_fusion_fuel_not_treated_as_general_chemistry(self):
        a=fit_review.review_job(job('Senior Fuel Scientist',
            'Your mission: Optimize fuel science laboratory protocols and undertake TGA. '
            'Your profile: Experience with hydrogen isotope exchange, tritium handling and fusion fuel research is required. '
            'Why us: Innovative work and benefits.'))
        self.assertIn('Fusion fuel / isotope chemistry', a['technical_gaps_to_verify'])
        self.assertNotEqual(a['technical_review'], 'Multiple method overlaps')

    def test_no_false_must_have_from_software_footer(self):
        a=fit_review.review_job(job('Research Scientist – Silica',
             'Your mission: Develop silica aerogels with sol-gel. Your profile: PhD in chemistry. '
             'Why us: Our software department maintains CAD and FEA platforms.'))
        self.assertIn('Silica / sol-gel materials',a['method_overlap'])
        self.assertFalse(any('CAD' in x for x in a['technical_gaps_to_verify']))


if __name__=='__main__':
    unittest.main()
