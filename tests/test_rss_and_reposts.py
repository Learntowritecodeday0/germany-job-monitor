import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

class RSSAndRepostTests(unittest.TestCase):
    def test_parse_official_rss(self):
        xml='''<rss version="2.0"><channel><title>Jobs</title><item><title>Materials Research Scientist (m/w/d)</title><link>https://jobs.mytum.de/jobs/123</link><guid>job-123</guid><description>Silica characterization</description><pubDate>Tue, 10 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'''
        c={'name':'TUM','slug':'tum','platform':'rss','careers_url':'https://jobs.mytum.de/jobs/','feed_url':'https://jobs.mytum.de/jobs/wissenschaftler/asRss'}
        jobs=monitor.parse_rss(c,ET.fromstring(xml))
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['title'],'Materials Research Scientist (m/w/d)')
        self.assertEqual(jobs[0]['published_at'],'2026-11-10T12:00:00+00:00')
        self.assertEqual(jobs[0]['location'],'') # no invented university worksite

    def test_reappearance_same_key(self):
        c={'companies':[{'name':'Example','slug':'example','platform':'rss','careers_url':'https://example.edu','feed_url':'https://example.edu/rss'}]}
        job={'key':'rss:example:one','company':'Example','title':'Nanoparticle Scientist','location':'Munich','description':'Nanoparticle synthesis and DoE', 'url':'https://example.edu/job'}
        t1='2026-11-10T10:00:00+00:00';t2='2026-11-10T12:00:00+00:00';t3='2026-11-11T10:00:00+00:00'
        with patch.object(monitor,'fetch_company',side_effect=[[job],[],[job]]):
            state=monitor.update(c,{'jobs':{},'sources':{}},t1)
            state=monitor.update(c,state,t2)
            self.assertFalse(state['jobs'][job['key']]['active'])
            state=monitor.update(c,state,t3)
        self.assertEqual(state['jobs'][job['key']]['reopen_count'],1)
        self.assertEqual(state['jobs'][job['key']]['reopened_at'],t3)
        self.assertEqual(state['jobs'][job['key']]['first_detected'],t1)

    def test_unrelated_specialist_titles_hidden(self):
        for t in ['Photonics Circuit Designer','Senior Battery Algorithms Engineer','Electronics Architect','Senior FPGA Designer','Working Student Chemistry','Praktikant Chemie','Senior Python SDK Engineer','Process Engineer Electric Motors for Robotics']:
            with self.subTest(title=t):
                self.assertTrue(monitor.qualification_preference({'title':t})['hide_by_default'],t)
        for t in ['Chemical Process Engineer','R&D Manager - Silica Materials','Material Scientist - Electronic Coatings','Process Engineer - Sol-Gel']:
            with self.subTest(title=t):
                self.assertFalse(monitor.qualification_preference({'title':t})['hide_by_default'],t)

if __name__=='__main__':unittest.main()
