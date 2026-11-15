"""Source proposals never become counted objects without complete ID review."""
import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from server import count_refinement as cr, deep_reader, store


class SourceReconciliation(unittest.TestCase):
    def setUp(self):
        self.initial={'operation':'count','value':2,'unit':'count','method':'source_inspection_agent',
            'evidence':[{'bbox':[.1,.1,.2,.2],'label':'Seat A'}, {'bbox':[.3,.1,.4,.2],'label':'Empty locator'}]}
        self.entries=[{'id':0,'kind':'existing locator to check','old_index':1,'bbox':[.3,.1,.4,.2]},
                      {'id':1,'kind':'new source form','bbox':[.6,.6,.7,.7]}]
        self.review={'accept_new':[{'id':1,'label':'Task chair at desk','category':'chair'}],
                     'confirm_existing':[],'reject':[0],'uncertain':[],'complete':True,'reason':'Located source objects'}

    def test_rejects_empty_locator_and_adds_source_reviewed_new_shape(self):
        original=copy.deepcopy(self.initial)
        result=cr.reconcile(self.initial,self.entries,[(self.entries,self.review)],['chair'],page=3)
        self.assertEqual(result['value'],2)
        self.assertEqual(result['evidence'][1]['bbox'],[.6,.6,.7,.7])
        self.assertEqual(result['evidence'][1]['page'],3)
        self.assertFalse(result['evidence'][1]['source_verified'])
        self.assertTrue(result['needs_review'])
        self.assertEqual(self.initial,original)

    def test_missing_duplicate_or_invented_ids_cannot_produce_a_total(self):
        for change in ({'reject':[]},{'reject':[0,0]},{'reject':[900]},{'confirm_existing':[0],'reject':[0]},
                       {'uncertain':[0],'reject':[]},{'complete':False}):
            with self.subTest(change=change):
                review={**self.review,**change}
                result=cr.reconcile(self.initial,self.entries,[(self.entries,review)],['chair'])
                self.assertIsNone(result['value'])
                self.assertFalse(result['can_review'])

    def test_semantic_category_and_old_new_id_roles_are_checked(self):
        self.assertFalse(cr.valid_review(self.entries,{**self.review,'accept_new':[{'id':1,'label':'Cabinet','category':'cabinet'}]},['chair']))
        self.assertFalse(cr.valid_review(self.entries,{**self.review,'accept_new':[], 'confirm_existing':[1]},['chair']))
        self.assertFalse(cr.valid_review(self.entries,None,['chair']))
        result=cr.reconcile(self.initial,self.entries,[(self.entries,None)],['chair'])
        self.assertIsNone(result['value'])
        self.assertIsNone(cr.reconcile(self.initial,self.entries,[],['chair'])['value'])


class ResumeSourceInventory(unittest.TestCase):
    def test_retry_reuses_original_model_observations_but_changed_question_does_not(self):
        from server import count_reader
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.png';Image.new('RGB',(80,60),'white').save(source)
            initial={'operation':'count','value':1,'unit':'count','evidence':[{'bbox':[.1,.1,.2,.2]}]}
            with patch.dict(os.environ,{'STOA_COUNT_REFINEMENT':'on','STOA_PARTITIONED_COUNTS':'on'}), \
                 patch.object(store,'RUNTIME',Path(folder)/'runtime'), \
                 patch.object(deep_reader,'eligible',return_value=True), \
                 patch('server.llm._scoped_context',return_value={'page_count':1}), \
                 patch('server.llm.requested_quantity',return_value='count'), \
                 patch('server.rendering.render_region',return_value=Image.new('RGB',(80,60))), \
                 patch.object(count_reader,'eligible',return_value=True), \
                 patch.object(count_reader,'answer',return_value=initial) as first_pass, \
                 patch.object(cr,'refine',side_effect=[{'value':None,'retryable_analysis':True},initial,initial]) as refine:
                deep_reader.answer('Count chairs',{'page_count':1},source)
                # A cached typed count remains eligible even when the heuristic
                # question classifier cannot recognize the wording.
                with patch('server.llm.requested_quantity',return_value=None):
                    deep_reader.answer('Count chairs',{'page_count':1},source)
                self.assertEqual(first_pass.call_count,1)
                self.assertEqual(refine.call_args.args[5],initial)
                deep_reader.answer('Count windows',{'page_count':1},source)
                self.assertEqual(first_pass.call_count,2)
