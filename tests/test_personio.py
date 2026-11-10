import unittest
from unittest.mock import patch
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import monitor

COMPANY={"name":"AMSilk","platform":"personio","slug":"amsilk","careers_url":"https://amsilk.jobs.personio.com"}
XML = '<?xml version="1.0" encoding="UTF-8"?>\n<workzag-jobs>\n  <position><id>101</id><name>Scientist - Materials</name><office>Neuried</office><createdAt>2026-11-01T09:00:00Z</createdAt><jobDescriptions><jobDescription><name>Responsibilities</name><value><![CDATA[<p>Develop <b>silica</b> formulations and DoE tests.</p>]]></value></jobDescription></jobDescriptions></position>\n  <position><id>102</id><name>Field Scientist</name><office>Munich, USA</office><jobDescriptions><jobDescription><name>Tasks</name><value>Material science</value></jobDescription></jobDescriptions></position>\n</workzag-jobs>'

class PersonioTests(unittest.TestCase):
    def test_xml_parse_and_normalization(self):
        jobs=monitor.parse_personio(COMPANY,ET.fromstring(XML))
        self.assertEqual(len(jobs),2)
        j=jobs[0]
        self.assertEqual(j['key'],'personio:amsilk:101')
        self.assertEqual(j['location'],'Neuried')
        self.assertEqual(j['url'],'https://amsilk.jobs.personio.com/job/101')
        self.assertIn('silica formulations',j['description'])
        self.assertEqual(j['published_at'],None)
        self.assertEqual(j['source_created_at'],'2026-11-01T09:00:00Z')
        self.assertEqual(monitor.location_status(j),'germany')
        self.assertEqual(monitor.location_status(jobs[1]),'verify_location')

    def test_invalid_xml_fails(self):
        with self.assertRaises(ValueError):
            monitor.parse_personio(COMPANY,ET.fromstring('<html></html>'))

    def test_first_scan_baseline_and_subsequent_detection(self):
        jobs=monitor.parse_personio(COMPANY,ET.fromstring(XML))
        with patch.object(monitor,'fetch_company',return_value=jobs):
            state=monitor.update({'companies':[COMPANY]},{'jobs':{},'sources':{}},'2026-11-10T09:00:00Z')
            self.assertTrue(state['jobs']['personio:amsilk:101']['at_startup'])
            next_state=monitor.update({'companies':[COMPANY]},state,'2026-11-10T13:00:00Z')
        self.assertEqual(next_state['jobs']['personio:amsilk:101']['first_detected'],'2026-11-10T09:00:00Z')

    def test_xml_failures_preserve_jobs(self):
        job=monitor.parse_personio(COMPANY,ET.fromstring(XML))[0]
        state={'jobs':{job['key']:{**job,'active':True,'first_detected':'2026-11-10T09:00:00Z'}},'sources':{'AMSilk':{'initialized':True}}}
        with patch.object(monitor,'fetch_company',side_effect=ValueError('XML unavailable')):
            result=monitor.update({'companies':[COMPANY]},state,'2026-11-10T13:00:00Z')
        self.assertTrue(result['jobs'][job['key']]['active'])
        self.assertEqual(result['sources']['AMSilk']['status'],'error')

    def test_german_location_does_not_hide_foreign_worksite(self):
        self.assertEqual(monitor.location_status({'location':'USA','country':'DE'}),'outside')
        self.assertEqual(monitor.location_status({'location':'Munich / Portugal','country':'DE'}),'verify_location')

if __name__=='__main__':unittest.main()
