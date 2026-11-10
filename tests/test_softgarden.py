import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

COMPANY = {"name":"Siltronic", "slug":"siltronic", "platform":"softgarden",
           "careers_url":"https://siltronic.career.softgarden.de",
           "feed_url":"https://siltronic.career.softgarden.de/jobs.feed.json"}
FEED = {
    "@context":"https://schema.org", "@type":"DataFeed", "numberOfItems":2,
    "dataFeedElement":[
        {"@type":"DataFeedItem", "dateModified":"2026-11-08T07:46:40Z",
         "item":{"@type":"JobPosting", "title":"Scientist Surface Chemistry",
                 "identifier":{"@type":"PropertyValue", "value":12345},
                 "url":"https://siltronic.career.softgarden.de/jobs/12345/example",
                 "datePosted":"2026-11-08T11:00:00+01:00",
                 "description":"<p>Characterize <b>silica</b> materials with FTIR.</p>",
                 "jobLocation":{"@type":"Place","address":{"addressCountry":"Deutschland","addressLocality":"Burghausen","addressRegion":"Bayern"}}}},
        {"@type":"DataFeedItem",
         "item":{"@type":"JobPosting", "title":"Multi-site Chemist",
                 "identifier":{"value":999},
                 "url":"https://siltronic.career.softgarden.de/jobs/999/example",
                 "jobLocation":[{"address":{"addressLocality":"Munich","addressCountry":"Deutschland"}},
                                {"address":{"addressLocality":"Delft","addressCountry":"Netherlands"}}]}}
    ]}

class SoftgardenTests(unittest.TestCase):
    def test_public_json_ld_feed(self):
        a,b=monitor.parse_softgarden(COMPANY, FEED)
        self.assertEqual(a['key'],'softgarden:siltronic:12345')
        self.assertEqual(a['published_at'],'2026-11-08T11:00:00+01:00')
        self.assertEqual(a['source_modified_at'],'2026-11-08T07:46:40Z')
        self.assertEqual(a['description'],'Characterize silica materials with FTIR.')
        self.assertEqual(monitor.location_status(a),'germany')
        self.assertEqual(monitor.location_status(b),'verify_location')
    def test_feed_errors_not_empty_jobs(self):
        with self.assertRaises(ValueError):
            monitor.parse_softgarden(COMPANY, {'@type':'DataFeed'})
        with self.assertRaises(ValueError):
            monitor.parse_softgarden(COMPANY, {'@type':'Collection','dataFeedElement':[]})
        self.assertEqual(monitor.parse_softgarden(COMPANY,{'@type':'DataFeed','dataFeedElement':[]}),[])
    def test_dispatch_to_public_feed(self):
        with patch.object(monitor,'get_json',return_value=FEED) as fetch:
            data=monitor.fetch_company(COMPANY)
        fetch.assert_called_once_with(COMPANY['feed_url'])
        self.assertEqual(len(data),2)
    def test_failed_feed_preserves_previous_jobs(self):
        a=monitor.parse_softgarden(COMPANY,FEED)[0]
        old={**a,'first_detected':'2026-11-10T09:00:00Z','active':True}
        state={'jobs':{a['key']:old},'sources':{'Siltronic':{'initialized':True,'count':1}}}
        with patch.object(monitor,'fetch_company',side_effect=ValueError('feed missing')):
            result=monitor.update({'companies':[COMPANY]},state,'2026-11-10T14:00:00Z')
        self.assertEqual(result['sources']['Siltronic']['status'],'error')
        self.assertTrue(result['jobs'][a['key']]['active'])

if __name__ == '__main__':
    unittest.main()
