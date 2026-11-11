"""Regression tests: official TUM RSS includes two near-identical postings."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import monitor

TUM = {"name":"Technische Universität München — wissenschaftliche Stellen", "slug":"tum-wissenschaftler", "platform":"rss", "careers_url":"https://jobs.mytum.de/jobs/"}
DATE = "2026-10-20T10:00:00+00:00"
CONTENT = ("The Chair of Complex Soft Matter at the TUM School of Life Sciences seeks "
           "a research associate in multivalent colloid science to synthesize and "
           "characterize nanoparticles for medicine and diagnostics using molecular self assembly.")
TITLE = "Research Associate in Supramolecular Colloidal Nanomaterials for Medicine and Diagnostics (Doctoral Research)"

def item(suffix, title=TITLE, description=CONTENT, date=DATE):
    return {"key":"rss:tum-wissenschaftler:"+suffix, "company":TUM["name"], "title":title,
            "description":description, "location":"", "country":"", "url":"https://jobs.mytum.de/jobs/wissenschaftler/NewsArticle_"+suffix+".html",
            "published_at":date, "source_mode":"rss_summary", "platform":"rss"}

class TUMRSSDedupTests(unittest.TestCase):
    def test_slightly_reworded_same_posting_merges(self):
        one=item('first')
        two=item('second',title=TITLE.replace('Doctoral Research','Doctoral research'),description=CONTENT.replace('medicine and diagnostics','medicine/diagnostics'))
        result=monitor.deduplicate_rss([one,two])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['duplicates_merged'],1)
        self.assertIn('rss:tum-wissenschaftler:second',result[0]['duplicate_keys'])

    def test_same_title_distinct_projects_not_merged(self):
        result=monitor.deduplicate_rss([item('first'), item('second',description='A different research group will develop ceramic coatings for aerospace engines and advanced durability testing. No nanoparticle medicine work is involved.')])
        self.assertEqual(len(result),2)

    def test_different_dates_not_merged_to_preserve_reposts(self):
        result=monitor.deduplicate_rss([item('first'),item('second',date='2026-11-11T10:00:00+00:00')])
        self.assertEqual(len(result),2)

    def test_new_feed_order_preserves_previous_representative(self):
        previous={'rss:tum-wissenschaftler:second':{'first_detected':'2026-11-10T14:00:00+00:00','active':True}}
        two=item('second',title=TITLE.replace('Doctoral Research','Doctoral research'),description=CONTENT.replace('medicine and diagnostics','medicine/diagnostics'))
        merged=monitor.deduplicate_rss([item('first'),two],previous)
        self.assertEqual(merged[0]['key'],'rss:tum-wissenschaftler:second')
        self.assertIn('rss:tum-wissenschaftler:first',merged[0]['duplicate_keys'])

    def test_prior_existing_duplicates_become_one_without_new_detection(self):
        a=item('first');b=item('second',title=TITLE.replace('Doctoral Research','Doctoral research'),description=CONTENT.replace('medicine and diagnostics','medicine/diagnostics'))
        old_state={'jobs':{}, 'sources':{TUM['name']:{'initialized':True,'count':2,'status':'ok'}}}
        for j in (a,b):
            old_state['jobs'][j['key']]={**j,'active':True,'at_startup':True,'first_detected':'2026-11-10T13:00:00+00:00', 'last_seen':'2026-11-10T13:00:00+00:00'}
        with patch.object(monitor,'fetch_company',return_value=[b,a]):
            new=monitor.update({'companies':[TUM]},old_state,'2026-11-11T14:00:00+00:00')
        active=monitor.public_data(new,'2026-11-11T14:00:00+00:00')['jobs']
        self.assertEqual(len(active),1)
        self.assertTrue(active[0]['at_startup'])
        self.assertEqual(active[0]['first_detected'],'2026-11-10T13:00:00+00:00')
        self.assertEqual(new['sources'][TUM['name']]['duplicates_removed'],1)
        self.assertEqual(new['sources'][TUM['name']]['count'],1)
        self.assertTrue(active[0]['hide_by_default'])  # pursuing first PhD rather than postdoc
        self.assertEqual(active[0]['reopen_count'],0)

    def test_postdoctoral_not_hidden(self):
        self.assertFalse(monitor.qualification_preference({'title':'Postdoctoral Researcher – Nanoparticle Chemistry'})['hide_by_default'])

if __name__=='__main__': unittest.main()
