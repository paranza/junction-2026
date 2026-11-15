"""Coverage and accounting of partitioned counts, without model calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from server import count_reader,llm,store


class PartitionedSourceCounts(unittest.TestCase):
    def setUp(self):
        self.doc={'page_count':1,'pages':[{'page':1,'width':8000,'height':5000,'words':[]}],'objects':[]}
        self.plan=[([0,0,.5,1],[0,0,.6,1]),([.5,0,1,1],[.4,0,1,1])]
        self.image=Image.new('RGB',(32,32),'white')

    def call(self,request,review=None,**kwargs):
        def dispatch(content,**kwargs):
            result=request(content,**kwargs)
            if kwargs.get('schema') is count_reader.AUDIT_SCHEMA:
                return review(result) if review else {'keep_ids':list(range(len(result['items']))),
                    'added':[],'complete':result['complete'],'warnings':result['warnings'],'coverage_note':result['coverage_note']}
            return result
        with patch.object(count_reader,'tiles',return_value=iter(self.plan)),\
             patch('server.rendering.render_region',return_value=self.image),patch.object(llm,'_request',side_effect=dispatch),\
             patch('server.drawing_tools.fingerprint',return_value='mock-source'),\
             patch('server.inspection_cache.InspectionCache.get',return_value=None),\
             patch('server.inspection_cache.InspectionCache.put'):
            return count_reader.answer('How many doors?',self.doc,Path('new.png'),1,[0,0,1,1],self.image,model='test',policy={},**kwargs)

    def test_overlapping_context_has_disjoint_ownership_and_page_coordinates(self):
        def request(content,**kwargs):
            first='Tile 1/2.' in content[0]['text']
            return {'items':[{'label':'Door','bbox':[.75,.4,.85,.5]}] if first else
                    [{'label':'Door duplicate from left core','bbox':[.08,.4,.18,.5]},
                     {'label':'Door','bbox':[.4,.4,.5,.5]}],
                    'complete':True,'warnings':[],'coverage_note':'Source core inspected'}
        result=self.call(request)
        self.assertEqual(result['value'],2)
        self.assertAlmostEqual(result['evidence'][0]['bbox'][0],.45)
        self.assertAlmostEqual(result['evidence'][1]['bbox'][0],.64)
        self.assertEqual(len(result['inspection']),2)
        self.assertTrue(all(not e['source_verified'] for e in result['evidence']))

    def test_incomplete_or_invalid_tile_cannot_publish_partial_count(self):
        for invalid in (False,True):
            def request(content,**kwargs):
                return {'items':[{'label':'Door','bbox':[0,.2,.3,.3] if not invalid else [9,9,10,10]}],
                        'complete':invalid,'warnings':[],'coverage_note':'Unresolved'}
            result=self.call(request)
            self.assertIsNone(result['value'])
            self.assertEqual(result['status'],'insufficient_evidence')

    def test_complete_empty_coverage_is_an_actual_zero(self):
        result=self.call(lambda *args,**kw:{'items':[],'complete':True,'warnings':[],'coverage_note':'No matching objects'})
        self.assertEqual(result['value'],0)

    def test_plan_is_bounded_and_covers_selection_exactly(self):
        bounds=[.12,.2,.94,.8];plan=list(count_reader.tiles(self.doc,1,bounds))
        area=sum((c[2]-c[0])*(c[3]-c[1]) for c,_ in plan)
        self.assertAlmostEqual(area,(bounds[2]-bounds[0])*(bounds[3]-bounds[1]))
        self.assertLessEqual(len(plan),count_reader.MAX_TILES)
        for core,crop in plan:
            self.assertTrue(bounds[0]<=crop[0]<=core[0]<core[2]<=crop[2]<=bounds[2])
            self.assertTrue(bounds[1]<=crop[1]<=core[1]<core[3]<=crop[3]<=bounds[3])
        self.assertTrue(count_reader.owned([.49,.3,.51,.4],[.5,0,1,1],[0,0,1,1]))
        self.assertFalse(count_reader.owned([.49,.3,.51,.4],[0,0,.5,1],[0,0,1,1]))

    def test_small_selection_does_not_trigger_whole_page_partitioning(self):
        self.assertTrue(count_reader.eligible(self.doc,Path('x.png'),1,[0,0,1,1]))
        self.assertFalse(count_reader.eligible(self.doc,Path('x.png'),1,[0,0,.1,.1]))
        self.assertFalse(count_reader.eligible(self.doc,Path('x.ifc'),1,[0,0,1,1]))

    def test_parallel_usage_stays_with_original_message(self):
        def request(*args,**kwargs):
            ledger=llm._usage.get();ledger['model_calls']+=1;ledger['input_tokens']+=11
            return {'items':[],'complete':True,'warnings':[],'coverage_note':'No objects'}
        with llm.usage_scope(session_id='s',message_id='m'):
            self.call(request)
            self.assertEqual(llm._usage.get()['model_calls'],4)
            self.assertEqual(llm._usage.get()['input_tokens'],44)
            self.assertEqual(llm._usage.get()['_message_id'],'m')

    def test_source_audit_can_reject_false_proposals_and_add_missed_styles(self):
        self.plan=[([0,0,1,1],[0,0,1,1])]
        def proposals(*a,**kw):return {'items':[{'label':'Chair','bbox':[.1,.1,.2,.2]},
            {'label':'False wall pier','bbox':[.4,.4,.5,.5]}], 'complete':True,'warnings':[],'coverage_note':'Proposals'}
        result=self.call(proposals,lambda raw:{'keep_ids':[0],
            'added':[{'label':'Task chair','bbox':[.7,.7,.8,.8]}], 'complete':True,'warnings':[],'coverage_note':'Reviewed source'})
        self.assertEqual(result['value'],2)
        self.assertEqual([e['label'] for e in result['evidence']],['Chair','Task chair'])
        bad=self.call(proposals,lambda raw:{'keep_ids':[99],'added':[], 'complete':True,'warnings':[],'coverage_note':'Invalid ID'})
        self.assertIsNone(bad['value'])

    def test_incomplete_owned_scope_gets_one_bounded_local_resolution(self):
        requests=[]
        def source(content,**kwargs):
            requests.append(content[0]['text'])
            return {'items':[{'label':'Door','bbox':[.2,.2,.3,.3]}],
                    'complete':True,'warnings':[],'coverage_note':'Owned core inspected'}
        result=self.call(source,lambda raw:{'keep_ids':[0],'added':[], 'complete':False,
            'warnings':[],'coverage_note':'Excluded an object in overlap context'},resolution_policy={'thinking_level':'medium'})
        self.assertEqual(result['value'],2)
        self.assertEqual(sum(text.startswith('Resolve the incomplete') for text in requests),2)
        self.assertTrue(all(t['audit']['resolution_attempted'] for t in result['inspection']))

    def test_named_fractional_boxes_preserve_xy_axes_and_invalid_shapes_are_not_zero(self):
        self.assertEqual(count_reader.normalized_items([{'label':'Door','bbox':{
            'left':.1,'top':.2,'right':.3,'bottom':.4}}])[0]['bbox'],[.1,.2,.3,.4])
        self.assertIsNone(llm._mapped_box(count_reader.normalized_items(None)[0]['bbox'],[0,0,1,1]))

    def test_transient_source_failure_retains_other_tiles_and_retry_resumes(self):
        failed=[]
        def request(content,**kwargs):
            if 'Tile 1/2.' in content[0]['text'] and not failed:
                failed.append(True);raise llm.ModelError('Read timed out',recoverable=True)
            if kwargs['schema'] is count_reader.AUDIT_SCHEMA:
                return {'keep_ids':[0],'added':[],'complete':True,'warnings':[],'coverage_note':'Source checked'}
            return {'items':[{'label':'Door','bbox':[.2,.2,.3,.3]}],
                    'complete':True,'warnings':[],'coverage_note':'Source checked'}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'new.png';self.image.save(path)
            with patch.object(store,'RUNTIME',Path(folder)/'runtime'), \
                 patch.object(count_reader,'tiles',side_effect=lambda *a:iter(self.plan)), \
                 patch('server.rendering.render_region',return_value=self.image), \
                 patch.object(llm,'_request',side_effect=request) as calls:
                first=count_reader.answer('How many doors?',self.doc,path,1,[0,0,1,1],self.image,model='test',policy={})
                self.assertIsNone(first['value']);self.assertTrue(first['retryable_analysis'])
                second=count_reader.answer('How many doors?',self.doc,path,1,[0,0,1,1],self.image,model='test',policy={})
                self.assertEqual(second['value'],2)
                self.assertEqual(second['count_inspection']['cached_tiles'],1)
                self.assertEqual(calls.call_count,5)


if __name__=='__main__':unittest.main()
