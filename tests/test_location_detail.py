import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import location_detail as ld

class LocationDetailTests(unittest.TestCase):
 def test_munich_region(self):
  x=ld.format_worksites({'location':'Munich HQ', 'country':'Germany'})
  self.assertEqual((x['worksite_city'],x['worksite_state'],x['worksite_country']),('Munich','Bayern','Germany'))
 def test_alzenau_with_bavaria(self):
  x=ld.format_worksites({'location':'Alzenau, Bavaria, Germany'})
  self.assertEqual((x['worksite_city'],x['worksite_state'],x['worksite_country']),('Alzenau','Bayern','Germany'))
 def test_zwickau(self):
  x=ld.format_worksites({'location':'Zwickau'})
  self.assertEqual(x['worksite_state'],'Sachsen')
 def test_aachen(self):
  x=ld.format_worksites({'location':'Aachen, Germany'})
  self.assertEqual(x['worksite_state'],'Nordrhein-Westfalen')
 def test_geretsried(self):
  x=ld.format_worksites({'location':'Geretsried, Deutschland'})
  self.assertEqual(x['worksite_state'],'Bayern')
 def test_multinational_explicit(self):
  x=ld.format_worksites({'location':'Munich HQ; Delft', 'country':'Germany'})
  self.assertTrue(x['worksite_multiple'])
  self.assertEqual(x['worksite_sites'][0]['country'],'Germany')
  self.assertEqual(x['worksite_sites'][1]['country'],'Netherlands')
  self.assertEqual(x['worksite_country'],'Germany / Netherlands')
 def test_multiple_unnamed_site_not_assumed_munich(self):
  x=ld.format_worksites({'location':'EDMO Manufacturing & Testing Facility', 'country':'Germany'})
  self.assertIsNone(x['worksite_city'])
  self.assertIsNone(x['worksite_state'])
  self.assertEqual(x['worksite_country'],'Germany')
  self.assertFalse(x['worksite_city_verified'])
 def test_country_only(self):
  x=ld.format_worksites({'location':'Germany'})
  self.assertIsNone(x['worksite_city'])
  self.assertEqual(x['worksite_country'],'Germany')
 def test_no_company_headquarter_guess(self):
  x=ld.format_worksites({'company':'VÆRIDION','location':'','country':''})
  self.assertIsNone(x['worksite_city'])
  self.assertIsNone(x['worksite_country'])
 def test_hessen_not_essen(self):
  x=ld.format_worksites({'location':'Hessen, Deutschland'})
  self.assertEqual(x['worksite_state'],'Hessen')
  self.assertIsNone(x['worksite_city'])
 def test_country_only_and_german_site(self):
  x=ld.format_worksites({'location':'United States; Canada; Aachen, Germany'})
  self.assertTrue(x['worksite_multiple'])
  self.assertIn('Germany',x['worksite_country'])
  self.assertIn('United States',x['worksite_country'])
  self.assertIn('Canada',x['worksite_country'])
 def test_no_field_clobber(self):
  j={'location':'Ulm','match_band':'Review first','citizenship_restriction_detected':True}
  j.update(ld.format_worksites(j))
  self.assertEqual(j['match_band'],'Review first')
  self.assertTrue(j['citizenship_restriction_detected'])

if __name__=='__main__': unittest.main()
