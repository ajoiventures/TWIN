import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_replay import replay,validate

class ReplayTests(unittest.TestCase):
    registry={'source_snapshot':'s1','records':[{'entity_id':'a'}]}
    def event(self,**changes):
        row=dict(event_id='e1',entity_id='a',source_snapshot='s1',mode='observed',source_id='source',sensor_id='camera',event_time='2026-10-28T12:00:00Z',ingested_time='2026-10-28T12:01:00Z',metric='count',value=3,unit='vehicles',confidence=.8,evidence_ref='local:test-only')
        row.update(changes);return row
    def test_duplicates_order_and_late_arrival(self):
        old=self.event();new=self.event(event_id='e2',event_time='2026-10-28T12:02:00Z',ingested_time='2026-10-28T12:03:00Z',value=4)
        late=self.event(event_id='e0',event_time='2026-10-28T11:59:00Z',ingested_time='2026-10-28T12:04:00Z',value=1)
        args=(self.registry,'2026-10-28T12:05:00Z','observed')
        result=replay([new,old,late,copy.deepcopy(old)],*args)
        self.assertEqual(result,replay([old,late,new],*args));self.assertEqual(result['rows'][0]['value'],4)
        before=replay([old,new,late],self.registry,'2026-10-28T12:05:00Z','observed',known_at='2026-10-28T12:02:00Z')
        self.assertEqual(before['included_event_ids'],['e1'])
    def test_modes_and_sources_never_merge(self):
        rows=[self.event(),self.event(event_id='sim',mode='simulated',run_id='r',value=99),self.event(event_id='other',source_id='other',value=8)]
        observed=replay(rows,self.registry,'2026-10-28T12:10:00Z','observed')
        self.assertEqual([r['value'] for r in observed['rows']],[8,3]);self.assertTrue(all(r['stale'] for r in observed['rows']))
        self.assertEqual(replay(rows,self.registry,'2026-10-28T12:10:00Z','synthetic')['rows'],[])
    def test_conflicting_duplicate_unknown_identity_and_bad_metadata_rejected(self):
        with self.assertRaises(ValueError):validate([self.event(),self.event(value=4)],self.registry)
        for changes in [dict(entity_id='missing'),dict(source_snapshot='old'),dict(event_time='2026-10-28T12:00:00'),dict(value=float('nan')),dict(confidence=2),dict(mode='synthetic',run_id=''),dict(ingested_time='2026-10-28T11:59:00Z'),dict(evidence_ref='')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate([self.event(**changes)],self.registry)
    def test_empty_is_not_zero_and_future_events_excluded(self):
        result=replay([self.event()],self.registry,'2026-10-28T11:59:00Z','observed')
        self.assertEqual(result['rows'],[]);self.assertEqual(result['included_event_ids'],[])

if __name__=='__main__':unittest.main()
