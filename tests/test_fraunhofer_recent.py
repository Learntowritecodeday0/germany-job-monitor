import unittest
from unittest.mock import patch
import monitor
import notify

C = {'name': 'Fraunhofer — recent official postings',
     'slug':'fraunhofer-official','platform':'successfactors_recent',
     'careers_url':'https://jobs.fraunhofer.de/',
     'search_url':'https://jobs.fraunhofer.de/search/?q=&sortColumn=referencedate&sortDirection=desc',
     'recent_pages':3}

def html_page(records):
    rows = ''.join(f'<tr class="data-row"><td class="colTitle"><a href="/job/{slug}/{jobid}/">{title}</a></td><td class="colLocation">{location}</td><td class="colInstitute">ISC</td></tr>'
                   for slug,jobid,title,location in records)
    return '<table id="searchresults">' + rows + '</table>'

A = ('Wuerzburg-Materials-Scientist', '1234001', 'Materials Scientist — Sol-Gel', 'Würzburg')
B = ('Berlin-Software', '1234002', 'Software Developer', 'Berlin')
D = ('Berlin-Analytik', '1234003', 'Wissenschaftliche*r Mitarbeiter*in — chemische Analytik', 'Berlin')

class SuccessFactorsRecentTests(unittest.TestCase):
    def test_official_links_and_locations_and_title_filter(self):
        content = html_page([A,B,D]) + '<a href="https://imposter.example/job/X/99999/">Materials Scientist</a>'
        jobs = monitor.parse_successfactors_recent(C, content)
        self.assertEqual(len(jobs),2)
        self.assertEqual({x['location'] for x in jobs}, {'Würzburg','Berlin'})
        self.assertTrue(all(x['url'].startswith('https://jobs.fraunhofer.de/job/') for x in jobs))
        self.assertTrue(all(x['source_mode']=='recent_title_only' for x in jobs))
    def test_no_job_links_is_error_not_zero(self):
        with self.assertRaises(ValueError):
            monitor.parse_successfactors_recent(C,'<html><body>Temporarily unavailable</body></html>')
    def test_network_uses_bounded_recent_pages(self):
        with patch.object(monitor,'get_html',side_effect=[html_page([A]),html_page([D]),html_page([A])]) as get:
            jobs=monitor.fetch_successfactors_recent(C)
        self.assertEqual(len(jobs),2)
        self.assertEqual(get.call_count,3)
        self.assertIn('startrow=50',get.call_args.args[0])
    def test_reject_external_or_insecure_search_url(self):
        bad={**C,'search_url':'http://jobs.fraunhofer.de/search/'}
        with self.assertRaises(ValueError):monitor.fetch_successfactors_recent(bad)
        bad={**C,'search_url':'https://jobs.fakefraunhofer.de/search/'}
        with self.assertRaises(ValueError):monitor.fetch_successfactors_recent(bad)
    def test_partial_scan_does_not_mark_missing_as_closed_or_reopened(self):
        state={'jobs':{},'sources':{}}
        with patch.object(monitor,'fetch_company',return_value=monitor.parse_successfactors_recent(C,html_page([A]))):
            state=monitor.update({'companies':[C]},state,'2026-11-12T10:00:00+00:00')
        key=next(iter(state['jobs']))
        self.assertTrue(state['jobs'][key]['active'])
        self.assertTrue(state['jobs'][key]['at_startup'])
        with patch.object(monitor,'fetch_company',return_value=monitor.parse_successfactors_recent(C,html_page([D]))):
            state=monitor.update({'companies':[C]},state,'2026-11-12T14:00:00+00:00')
        self.assertTrue(state['jobs'][key]['active'])
        self.assertEqual(state['jobs'][key]['reopen_count'],0)
        with patch.object(monitor,'fetch_company',return_value=monitor.parse_successfactors_recent(C,html_page([A]))):
            state=monitor.update({'companies':[C]},state,'2026-11-12T18:00:00+00:00')
        self.assertEqual(state['jobs'][key]['reopen_count'],0)
        self.assertTrue(state['sources'][C['name']]['recent_window'])
    def test_email_never_alerts_title_only_search(self):
        job=monitor.parse_successfactors_recent(C,html_page([A]))[0]
        job.update({'active':True,'at_startup':False,'match_band':'Review first',
                    'hide_by_default':False,'location_status':'germany',
                    'first_detected':'2026-11-12T11:00:00+00:00'})
        self.assertEqual(notify.candidates({'jobs':{job['key']:job}, 'alerts_started_at':'2026-11-11T11:00:00+00:00'}),[])

if __name__=='__main__':unittest.main()
