"""Regression tests for the QuantumDiamonds and TUM source repairs."""
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor

ROOT = Path(__file__).resolve().parents[1]
RSS_SCIENTIFIC_EMPTY = '<rss version="2.0"><channel><title>TUM academic jobs</title></channel></rss>'
RSS_PUBLIC = '''<rss version="2.0"><channel><title>TUM all jobs</title><item>
<title>Materials Research Scientist (m/w/d)</title>
<link>http://portal.mytum.de/jobs/wissenschaftler/NewsArticle_20261111_123000</link>
<description>Laboratory characterization of nanoparticle materials</description>
<guid>tum-123</guid></item></channel></rss>'''
RSS_PUBLIC_RELATIVE = '''<rss version="2.0"><channel><item><title>Instrument Scientist</title>
<link>/jobs/wissenschaftler/NewsArticle_20261111_170000</link></item></channel></rss>'''

class SourceRecoveryTests(unittest.TestCase):
    def config(self):
        d=json.loads((ROOT/'config/companies.json').read_text(encoding='utf-8'))
        return d

    def test_quantumdiamonds_uses_verified_de_board(self):
        c=next(x for x in self.config()['companies'] if x['name']=='QuantumDiamonds')
        self.assertEqual(c['careers_url'],'https://quantum-diamond.jobs.personio.de')
        self.assertEqual(c['platform'],'personio')

    def test_quantumdiamonds_html_fallback_on_disabled_xml(self):
        c=next(x for x in self.config()['companies'] if x['name']=='QuantumDiamonds')
        err=HTTPError(c['careers_url']+'/xml',404,'Not found',None,None)
        html='<html><a href="/job/2816754"><h2>Product Manager (f/m/d)</h2></a></html>'
        with patch.object(monitor,'get_xml',side_effect=err),patch.object(monitor,'get_html',return_value=html):
            jobs=monitor.fetch_company(c)
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['url'],'https://quantum-diamond.jobs.personio.de/job/2816754')

    def test_tum_uses_general_official_feed_when_scientific_is_empty(self):
        c=next(x for x in self.config()['companies'] if x['platform']=='rss')
        self.assertEqual(c['fallback_feed_url'],'https://jobs.mytum.de/jobs/asRss')
        feeds=[ET.fromstring(RSS_SCIENTIFIC_EMPTY),ET.fromstring(RSS_PUBLIC)]
        with patch.object(monitor,'get_xml',side_effect=feeds) as get:
            jobs=monitor.fetch_company(c)
        self.assertEqual(get.call_count,2)
        self.assertEqual(len(jobs),1)
        self.assertTrue(jobs[0]['feed_fallback'])
        self.assertEqual(jobs[0]['url'],'https://portal.mytum.de/jobs/wissenschaftler/NewsArticle_20261111_123000')

    def test_relative_tum_rss_links_are_normalized(self):
        c=next(x for x in self.config()['companies'] if x['platform']=='rss')
        jobs=monitor.parse_rss(c,ET.fromstring(RSS_PUBLIC_RELATIVE))
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['url'],'https://jobs.mytum.de/jobs/wissenschaftler/NewsArticle_20261111_170000')

    def test_empty_both_tum_feeds_are_error_not_zero_vacancies(self):
        c=next(x for x in self.config()['companies'] if x['platform']=='rss')
        empty=ET.fromstring(RSS_SCIENTIFIC_EMPTY)
        with patch.object(monitor,'get_xml',return_value=empty):
            with self.assertRaisesRegex(ValueError,'both returned zero usable jobs'):
                monitor.fetch_company(c)

    def test_recovered_tum_initial_batch_is_not_alerted(self):
        c=next(x for x in self.config()['companies'] if x['platform']=='rss')
        initial_state={'sources':{c['name']:{'initialized':True,'count':0,'status':'ok'}},'jobs':{}}
        with patch.object(monitor,'get_xml',side_effect=[ET.fromstring(RSS_SCIENTIFIC_EMPTY),ET.fromstring(RSS_PUBLIC)]):
            data=monitor.update({'companies':[c]},initial_state,'2026-11-11T14:00:00+00:00')
        self.assertEqual(data['sources'][c['name']]['source_mode'],'public_rss_fallback')
        job=next(iter(data['jobs'].values()))
        self.assertTrue(job['at_startup'])

if __name__=='__main__': unittest.main()
