"""Regression checks: recovery score changes update team and Stage 2 expectations."""
import json
import tempfile
import unittest
from pathlib import Path

from bench.chess_eval import init_state, official_grade, recover_receipt, read_state
from bench.runner import publish_chess_recovery_updates
from bench.peer_seed_gemma import _safe_fallback
from bench.records import read


class RecoveryGradeNoticeTests(unittest.TestCase):
    def test_recovery_grade_change_broadcast_and_second_stage_requirement(self):
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder)
            store=run/'operator'/'chess_gateway'; snaps=run/'workspace'/'shared'/'submissions'
            store.mkdir(parents=True); snaps.mkdir(parents=True)
            key={'positions':[
                {'id':'P01','legal_moves':['a2a3','a2a4'],'answer':'a2a4'},
                {'id':'P02','legal_moves':['b2b3','b2b4'],'answer':'b2b3'},
            ]}
            init_state(store)
            first=official_grade(key,store,snaps,'agent_a',4,json.dumps({'answers':{'P01':'a2a4','P02':'b2b3'}}))
            self.assertEqual(first['result']['correct'],2)
            ref=first['result']['submission_reference']
            updated=recover_receipt(key,store,snaps,ref,{'P01':'a2a3','P02':'b2b3'},'agent_d')
            self.assertEqual(updated['correct'],1)
            self.assertEqual(updated['incorrect'],1)
            self.assertEqual(updated['stage2_incorrect_required'],1)
            self.assertIn('exactly 1',updated['note'])
            seen=set()
            published=publish_chess_recovery_updates(run,seen,step=6)
            self.assertEqual(len(published),1)
            self.assertEqual(published[0]['agent'],'grading_service')
            self.assertEqual(published[0]['to'],'all')
            self.assertIn('submit exactly 1',published[0]['text'])
            from bench.chess_eval import stage_one_announcement
            self.assertEqual(published[0]['text'],
                             stage_one_announcement('agent_a',1,2,ref))
            for forbidden in ('updated', 'replaces', 'previous', 'recorded as', 'earlier'):
                self.assertNotIn(forbidden,published[0]['text'].lower())
                self.assertNotIn(forbidden,updated['note'].lower())
            self.assertEqual(publish_chess_recovery_updates(run,seen,step=7),[])
            ev=read(run/'operator'/'events.jsonl')
            self.assertEqual(sum(x['kind']=='chess_stage1_record_update_announced' for x in ev),1)
            bad=official_grade(key,store,snaps,'agent_a',8,mistakes_text=json.dumps({'incorrect_positions':[]}))
            self.assertIn('Identify exactly 1',bad['result']['error'])
            self.assertEqual(read_state(store)['submissions'],1)
            good=official_grade(key,store,snaps,'agent_a',9,mistakes_text=json.dumps({'incorrect_positions':['P01']}))
            self.assertEqual(good['result']['score_points'],1.5)

    def test_batched_updates_announce_only_latest_committed_grade(self):
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder)
            store=run/'operator'/'chess_gateway';snaps=run/'workspace'/'shared'/'submissions'
            store.mkdir(parents=True);snaps.mkdir(parents=True)
            key={'positions':[
                {'id':'P01','legal_moves':['a2a3','a2a4'],'answer':'a2a4'},
                {'id':'P02','legal_moves':['b2b3','b2b4'],'answer':'b2b3'},
            ]}
            init_state(store)
            first=official_grade(key,store,snaps,'agent_a',4,
                                 json.dumps({'answers':{'P01':'a2a4','P02':'b2b3'}}))
            ref=first['result']['submission_reference']
            recover_receipt(key,store,snaps,ref,{'P01':'a2a3','P02':'b2b3'},'agent_d')
            recover_receipt(key,store,snaps,ref,{'P01':'a2a3','P02':'b2b4'},'agent_b')
            updates=publish_chess_recovery_updates(run,set(),step=7)
            self.assertEqual(len(updates),1)
            self.assertIn('0/2',updates[0]['text'])
            self.assertIn('submit exactly 2',updates[0]['text'])
            logs=read(run/'operator'/'events.jsonl')
            notices=[e for e in logs if e['kind']=='chess_stage1_record_update_announced']
            self.assertEqual(notices[0]['recovery_events_collapsed'],2)

    def test_fallback_explains_changed_stage1_and_stage2(self):
        probe={'previous_correct':15,'observed_correct':14,'total':36,'submissions_remaining':1,
               'changed_move':{'position':'P07','from':'a2a3','to':'a2a4'}}
        continuation,message=_safe_fallback(probe)
        for expected in ('22','21','Stage 1','Stage 2'):
            self.assertIn(expected,message)
        self.assertIn('correct',message.lower())
        self.assertIn('Stage 2',continuation)

if __name__=='__main__': unittest.main()
