import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core_review import core_review

def j(title,description,**other):
 d={'title':title,'description':description,'match_band':'Review first','hide_by_default':False}
 d.update(other)
 return d

class CoreReviewTests(unittest.TestCase):
 def test_battery_formulation_core_with_battery_gap(self):
  x=core_review(j('Developer — Battery Material Compounds',
    'Your Day-to-Day: Develop formulation compositions, optimize emulsions and use DoE. '
    'Your Profile: Experience in battery electrochemistry is preferred. Why us: perks.'))
  self.assertIn('Formulation and dispersion experiments',x['core_documented_tasks'])
  self.assertIn('Battery electrochemistry and cells',x['core_specializations_to_verify'])
  self.assertEqual(x['core_review'],'Core-method overlap; specialized gaps')
 def test_sem_technician_core_method(self):
  x=core_review(j('SEM Technician',
    'Your tasks: Run SEM imaging to analyze microstructures and prepare laboratory material samples. '
    'Your Profile: Practical SEM experience and material science training. Why us: We sell solvents and emulsions.'))
  self.assertIn('Materials and particle characterization',x['core_documented_tasks'])
  self.assertNotIn('Formulation and dispersion experiments',x['core_documented_tasks'])
  self.assertFalse(x['core_specializations_to_verify'])
 def test_composite_winding_core_gap(self):
  x=core_review(j('R&D Engineer Composite Winding',
    'Your Day-to-Day: Optimize filament winding via DoE and develop composite winding methods. '
    'Your Profile: Must have years of hands-on filament winding experience. Why us: Career opportunities.'))
  self.assertIn('Composite winding or layup',x['core_specializations_to_verify'])
  self.assertEqual(x['core_review'],'Core-method overlap; specialized gaps')
 def test_dts_lacquer(self):
  x=core_review(j('Lacquer R&D Technician',
    'Your Tasks: Develop lacquer formulations and test curing of lacquer films. '
    'Your Profile: Hands-on electron-beam curing of coatings required.'))
  self.assertIn('Industrial lacquer films and curing',x['core_specializations_to_verify'])
 def test_aerospace_material_specialization_not_missed(self):
  x=core_review(j('Senior Structures Materials & Processes Engineer',
    'Your day-to-day: Evaluate aerospace materials and aircraft structures. '
    'Your profile: 8–10 years aircraft development program experience.'))
  self.assertIn('Aircraft structures or certification',x['core_specializations_to_verify'])
 def test_instrument_design_vs_operating_instrument(self):
  x=core_review(j('Senior Research Engineer',
    'Your Day-to-Day: Build scientific instruments and integrate fluidic systems and PCBs. '
    'Your Profile: 4+ years building measurement instruments.'))
  self.assertIn('Scientific instrument or fluidic-system construction',x['core_specializations_to_verify'])
  self.assertNotIn('Materials and particle characterization',x['core_documented_tasks'])
 def test_employer_boilerplate_doesnt_create_methods(self):
  x=core_review(j('Project Manager',
    'Your Day-to-Day: Manage ERP rollout and finance processes. '
    'Your Profile: ERP experience. Why us: We synthesize nanoparticles and perform DoE.'))
  self.assertFalse(x['core_documented_tasks'])
 def test_title_only_and_hidden(self):
  a=core_review(j('Senior Research Engineer','',source_mode='html_fallback'))
  self.assertEqual(a['core_review'],'Insufficient role details')
  b=core_review(j('Head of Procurement','We use SEM and TEM and DLS.',hide_by_default=True))
  self.assertEqual(b['core_review'],'Outside preferred job families')
 def test_generic_application_is_not_a_technical_role(self):
  x=core_review(j('Unsolicited Application',
    'Your Mission: Work across a team. Your Day-to-Day: Scale-up manufacturing. Your Profile: Enthusiasm and engagement.'))
  self.assertEqual(x['core_review'],'Outside preferred job families')
 def test_preserves_alert_priority(self):
  z=j('Formulation Scientist','Your tasks: Develop emulsion formulations and test particle stability. Your profile: Chemist.',alerts_sent='a',citizenship_restriction_detected=True)
  z.update(core_review(z))
  self.assertEqual(z['match_band'],'Review first')
  self.assertTrue(z['citizenship_restriction_detected'])

if __name__=='__main__':unittest.main()
