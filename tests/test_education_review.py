import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from education_review import education_review
from qualification_priority import priority_review

def job(profile,**extra):
 d={'title':'Research scientist','description':'Your tasks: Characterize materials in the laboratory. Your Profile: '+profile+' Why us: Work with our team.'}
 d.update(extra)
 return d

class EducationReviewTests(unittest.TestCase):
 def test_bachelor_minimum_master_or_phd_preferred(self):
  d=education_review(job("Bachelor's degree minimum; MSc or PhD preferred. At least two years of experience."))
  self.assertEqual(d['minimum_level'],'Bachelor')
  self.assertEqual(d['preferred_level'],'Master / Diplom')
  self.assertFalse(d['possible_overqualified'])
 def test_master_or_phd_acceptable_not_phd_preferred(self):
  d=education_review(job('A master’s degree or PhD in materials science. At least five years experience.'))
  self.assertEqual(d['minimum_level'],'Master / Diplom')
  self.assertIsNone(d['preferred_level'])
  self.assertIn('Master or PhD accepted',d['alternative_routes'][0])
 def test_german_studium_and_promotion(self):
  d=education_review({'description':'Ihre Aufgaben: Chemische Synthesen. Ihr Profil: Abgeschlossenes Studium der Chemie. Eine Promotion ist von Vorteil. Wir bieten: Benefits.'})
  self.assertEqual(d['minimum_level'],'University degree / Studium (level unspecified)')
  self.assertEqual(d['preferred_level'],'PhD / Promotion')
 def test_german_ausbildung_only_overqualification_possible(self):
  d=education_review({'description':'Ihre Aufgaben: Analytische Prüfungen. Das bringen Sie mit: Erfolgreich abgeschlossene Ausbildung als Chemielaborant oder vergleichbar. Wir bieten: Benefits.'})
  self.assertEqual(d['minimum_level'],'Vocational training / Ausbildung')
  self.assertTrue(d['possible_overqualified'])
 def test_university_or_techniker_alternative_not_overqualification(self):
  d=education_review(job('Abgeschlossenes Studium der Chemie, Lacktechnik oder erfahrener Techniker.'))
  self.assertFalse(d['possible_overqualified'])
 def test_years_only_does_not_add_education(self):
  d=education_review(job('At least five years of professional experience in materials testing and quality control.'))
  self.assertEqual(d['status'],'not_specified')
  self.assertIsNone(d['minimum_level'])
 def test_title_only_no_education(self):
  d=education_review({'description':'', 'source_mode':'html_fallback'})
  self.assertEqual(d['status'],'unavailable')
 def test_bachelor_or_master(self):
  d=education_review(job('Bachelor or Master degree in chemistry is required.'))
  self.assertEqual(d['minimum_level'],'Bachelor')
 def test_masters_plural_and_technical_training_alternative(self):
  masters=education_review(job('Masters Degree in materials science, process engineering or similar.'))
  self.assertEqual(masters['minimum_level'],'Master / Diplom')
  alternative=education_review(job('Technical training or a bachelor’s or master’s degree in physics, chemistry or engineering.'))
  self.assertFalse(alternative['possible_overqualified'])
  self.assertTrue(alternative['alternative_routes'])
 def test_does_not_change_priority(self):
  j=job('A bachelor degree in chemistry and experience in DoE.',match_band='Possible')
  result=priority_review(j)
  self.assertEqual(j['match_band'],'Possible')
  self.assertIn('education_review',result)
  self.assertIn('qualification_priority',result)

if __name__=='__main__':unittest.main()
