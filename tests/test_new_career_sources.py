"""Regression tests for the PCT, fischer and CeramTec public job readers."""
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from pathlib import Path
import sys, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import monitor, notify
import location_detail
from career_adapters import (parse_pct_listing, enrich_pct_job,
    parse_ceramtec_listing, enrich_ceramtec_job,
    normalize_smartrecruiters_listing, enrich_smartrecruiters_job)

C = json.loads((Path(__file__).resolve().parents[1]/'config/companies.json').read_text())
COMP = {x['name']:x for x in C['companies']}
PCT = COMP['PCT Chemie']
CER = COMP['CeramTec — recent vacancies']
FIS = COMP['fischer Group']

PCT_PAGE = '''<html><table><tr><th>Stellentitel</th><th>Art</th><th>Ort</th></tr>
<tr><td>Chemiker / Naturwissenschaftler (m/w/d)</td><td>Vollzeit</td><td>Magstadt</td><td><a href="/pct-chemie/karriere/offene-stellen/chemiker-m-w-d">Details</a></td></tr>
<tr><td>Finanzbuchhaltung (m/w/d)</td><td>Teilzeit</td><td>Magstadt</td><td><a href="https://www.pct-chemie.de/pct-chemie/karriere/offene-stellen/finanzbuchhaltung">Details</a></td></tr>
</table><a href="https://malicious.example/pct-chemie/karriere/offene-stellen/fake">Chemiker</a></html>'''
PCT_DETAIL = '''<html><body><h1>Chemiker / Naturwissenschaftler (m/w/d)</h1>
<h2>Deine Aufgaben</h2><ul><li>Eigenständige Entwicklung, Synthese und Optimierung von Additiven.</li>
<li>Versuchsplanung und wissenschaftliche Dokumentation von Laborversuchen, Materialanalytik und Qualitätstests.</li></ul>
<h2>Das bringst du mit</h2><p>Abgeschlossenes Studium der Chemie und Deutschkenntnisse.</p>
<h2>Deine Benefits</h2><p>Benefits</p></body></html>'''
CER_PAGE='''<html><body><div>Online seit: 31.07.2026</div><a href="/Vacancies/4638/Description/1">Leiter (m/w/d) Arbeitsvorbereitung</a> | Lohmar
<div>Online seit: 30.07.2026</div><a href="/Vacancies/5678/Description/1">Materials Scientist (m/w/d)</a> | Marktredwitz
<a href="https://not-ceramtec.invalid/Vacancies/9999/Description/1">Fake job</a></body></html>'''
CER_DETAIL='''<html><body><h1>Materials Scientist (m/w/d)</h1><div>Standort:</div><div>Marktredwitz</div>
<h2>mit folgenden Aufgabenschwerpunkten:</h2><ul><li>Material synthesis and ceramic characterization.</li>
<li>Develop samples using microscopy and thermal characterization methods for production quality.</li></ul>
<h2>Ihr Profil:</h2><p>Degree in materials science and laboratory experience.</p><h2>Benefits</h2><p>Good job.</p></body></html>'''
FIS_LIST = {'limit':100,'offset':0,'totalFound':2,'content':[
    {'id':'744000159557829','name':'Chemiker (m/w/d) Produktentwicklung','location':{'city':'Denzlingen','region':'Baden-Württemberg','country':'de'},'releasedDate':'2026-11-11T12:00:00+01:00'},
    {'id':'7440090909','name':'Talent Acquisition Manager','location':{'city':'Waldachtal','country':'de'}}]}
FIS_DETAIL = {'postingUrl':'https://jobs.smartrecruiters.com/FischerGroup/744000159557829-chemiker-m-w-d-produktentwicklung',
              'jobAd':{'sections':{'jobDescription':{'text':'<p>Rezepturen und Formulierungen entwickeln.</p>'},
                                    'qualifications':{'text':'<p>Abgeschlossenes Studium der Chemie, sehr gute Deutschkenntnisse.</p>'}}}}

class CareerSourceTests(unittest.TestCase):
    def test_51_unique_sources_without_frozen_count(self):
        companies=C['companies']
        self.assertGreaterEqual(len(companies),51)
        self.assertEqual(len({x['name'] for x in companies}),len(companies))
        self.assertEqual(len({(x['platform'],x['slug']) for x in companies}),len(companies))

    def test_pct_list_uses_real_official_urls_and_advertised_location(self):
        jobs=parse_pct_listing(PCT,PCT_PAGE)
        self.assertEqual(len(jobs),2)
        self.assertIn('Chemiker / Naturwissenschaftler',jobs[0]['title'])
        self.assertEqual(jobs[0]['location'],'Magstadt')
        self.assertEqual(jobs[0]['source_mode'],'html_fallback')
        self.assertTrue(all('pct-chemie.de' in x['url'] for x in jobs))

    def test_pct_full_detail_and_incomplete_detail_warning(self):
        j=parse_pct_listing(PCT,PCT_PAGE)[0]
        self.assertEqual(enrich_pct_job(j,PCT_DETAIL)['source_mode'],'html_detail')
        self.assertIn('Materialanalytik',j['description'])
        self.assertNotIn('Benefits</p>',j['description'])
        j2=parse_pct_listing(PCT,PCT_PAGE)[0]
        enrich_pct_job(j2,'<h1>Chemiker / Naturwissenschaftler</h1>')
        self.assertEqual(j2['source_mode'],'html_fallback')

    def test_pct_page_failure_is_not_zero_vacancies(self):
        with self.assertRaises(ValueError):
            parse_pct_listing(PCT,'<html>Temporary error</html>')

    def test_ceramtec_link_filter_and_source_limit(self):
        jobs=parse_ceramtec_listing(CER,CER_PAGE)
        self.assertEqual(len(jobs),2)
        self.assertTrue(all(j['source_mode']=='recent_title_only' for j in jobs))
        self.assertTrue(all(j['url'].startswith('https://jobs.ceramtec-group.com/') for j in jobs))
        with self.assertRaises(ValueError):
            parse_ceramtec_listing(CER,'<h1>System maintenance</h1>')

    def test_ceramtec_detail_does_not_invent_worksite(self):
        j=parse_ceramtec_listing(CER,CER_PAGE)[1]
        enrich_ceramtec_job(j,CER_DETAIL)
        self.assertEqual(j['location'],'Marktredwitz')
        self.assertEqual(j['source_mode'],'html_detail')
        self.assertIn('Degree in materials science',j['description'])

    def test_new_german_worksites_are_not_guessed_from_hq(self):
        cases=[('Magstadt','Baden-Württemberg'),('Denzlingen','Baden-Württemberg'),
               ('Marktredwitz','Bayern'),('Lohmar','Nordrhein-Westfalen')]
        for city,state in cases:
            site=location_detail.format_worksites({'location':city,'country':'Germany'})
            self.assertEqual((site['worksite_city'],site['worksite_state'],site['worksite_country']),
                             (city,state,'Germany'))
            self.assertEqual(monitor.location_status({'location':city,'country':'Germany'}),'germany')
        unknown=location_detail.format_worksites({'location':'Headquarters','country':''})
        self.assertIsNone(unknown['worksite_city'])

    def test_smartrecruiters_posts_and_details(self):
        jobs=[normalize_smartrecruiters_listing(FIS,x) for x in FIS_LIST['content']]
        self.assertEqual(jobs[0]['country'],'de')
        self.assertIn('Denzlingen',jobs[0]['location'])
        self.assertEqual(jobs[0]['source_mode'],'api_list_only')
        enrich_smartrecruiters_job(jobs[0],FIS_DETAIL)
        self.assertEqual(jobs[0]['source_mode'],'api_detail')
        self.assertIn('Abgeschlossenes Studium',jobs[0]['description'])
        self.assertIn('produktentwicklung',jobs[0]['url'])

    def test_smartrecruiters_fetch_official_api_and_paginate(self):
        with patch.object(monitor,'get_json',side_effect=[FIS_LIST,FIS_DETAIL]) as get:
            jobs=monitor.fetch_company(FIS)
        self.assertEqual(len(jobs),2)
        self.assertEqual(get.call_count,2)
        self.assertIn('/FischerGroup/postings?limit=100&offset=0',get.call_args_list[0].args[0])
        self.assertEqual(jobs[0]['source_mode'],'api_detail')
        self.assertEqual(jobs[1]['source_mode'],'api_list_only')
        self.assertTrue(monitor.qualification_preference(jobs[1])['hide_by_default'])

    def test_incomplete_smartrecruiters_list_does_not_imply_no_jobs(self):
        with patch.object(monitor,'get_json',return_value={'content':[]}):
            with self.assertRaises(ValueError): monitor.fetch_company(FIS)

    def test_partial_ceramtec_window_never_marks_missing_as_closed(self):
        a,b=parse_ceramtec_listing(CER,CER_PAGE)
        at='2026-11-12T14:00:00+00:00'
        with patch.object(monitor,'fetch_company',return_value=[a]):
            state=monitor.update({'companies':[CER]},{'jobs':{},'sources':{}},at)
        key=a['key'];self.assertTrue(state['jobs'][key]['active'])
        with patch.object(monitor,'fetch_company',return_value=[b]):
            state=monitor.update({'companies':[CER]},state,'2026-11-12T16:00:00+00:00')
        self.assertTrue(state['jobs'][key]['active'])
        self.assertTrue(state['sources'][CER['name']]['recent_window'])
        self.assertEqual(state['jobs'][key]['reopen_count'],0)

    def test_first_scan_baseline_no_email(self):
        with patch.object(monitor,'get_html',side_effect=[PCT_PAGE,PCT_DETAIL,PCT_DETAIL]):
            state=monitor.update({'companies':[PCT]}, {'jobs':{},'sources':{}},'2026-11-12T13:00:00+00:00')
        self.assertTrue(all(x['at_startup'] for x in state['jobs'].values()))

    def test_title_only_does_not_send_priority_alert(self):
        job=normalize_smartrecruiters_listing(FIS,FIS_LIST['content'][0])
        job.update({'active':True,'at_startup':False,'hide_by_default':False,
                   'first_detected':'2026-11-12T15:00:00+00:00', 'match_band':'Review first'})
        self.assertEqual(notify.candidates({'jobs':{job['key']:job},
          'alerts_started_at':'2026-11-12T12:00:00+00:00'}),[])

    def test_failed_source_preserves_previous_jobs(self):
        j=parse_pct_listing(PCT,PCT_PAGE)[0]
        old={**j,'active':True,'first_detected':'2026-11-11T12:00:00+00:00'}
        state={'jobs':{j['key']:old},'sources':{PCT['name']:{'status':'ok','initialized':True,'count':1}}}
        with patch.object(monitor,'fetch_company',side_effect=HTTPError(PCT['careers_url'],403,'Forbidden',{},None)):
            result=monitor.update({'companies':[PCT]},state,'2026-11-12T16:00:00+00:00')
        self.assertTrue(result['jobs'][j['key']]['active'])
        self.assertEqual(result['sources'][PCT['name']]['status'],'error')

if __name__=='__main__':unittest.main()
