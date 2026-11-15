from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from PIL import Image
from server import route_reader as rr,llm
from server.drawing_tools import ToolError


class SourceRouteTakeoff(unittest.TestCase):
    def setUp(self):
        self.cache_dir=tempfile.TemporaryDirectory()
        self.cache_patch=patch('server.inspection_cache.store.RUNTIME',Path(self.cache_dir.name))
        self.cache_patch.start()

    def tearDown(self):
        self.cache_patch.stop();self.cache_dir.cleanup()

    def test_intent_is_length_not_nominal_diameter_or_hidden_quantity_substitution(self):
        self.assertTrue(rr.requested('How many metres of pipe centreline are drawn?'))
        self.assertTrue(rr.requested('Quanti metri di tubi ci sono nel progetto?'))
        self.assertTrue(rr.requested('How many feet of pipe are actually drawn?'))
        self.assertTrue(rr.requested('What is the 2D centerline length in metres of the incoming cold-water service?'))
        self.assertFalse(rr.requested('What is the nominal pipe diameter in metres?'))
        self.assertFalse(rr.requested('How many pipes are shown?'))
        self.assertFalse(rr.requested('What is the floor area?'))

    def test_clipping_owns_shared_boundary_once_and_retains_only_selected_geometry(self):
        path=[{'label':'Pipe','points':[[.1,.4],[.9,.4]]}]
        left=rr.clipped_paths(path,[0,0,1,1],[0,0,.5,1],[0,0,1,1])
        right=rr.clipped_paths(path,[0,0,1,1],[.5,0,1,1],[0,0,1,1])
        self.assertEqual(left,[[[.1,.4],[.5,.4]]]);self.assertEqual(right,[[[.5,.4],[.9,.4]]])
        boundary=[{'points':[[.5,.1],[.5,.9]]}]
        self.assertEqual(rr.clipped_paths(boundary,[0,0,1,1],[0,0,.5,1],[0,0,1,1]),[])
        self.assertEqual(len(rr.clipped_paths(boundary,[0,0,1,1],[.5,0,1,1],[0,0,1,1])),1)
        with self.assertRaises(ToolError):rr.clipped_paths([{'points':[[0,0],[2,1]]}],[0,0,1,1],[0,0,1,1],[0,0,1,1])

    def test_equipment_bodies_cut_paths_without_dropping_adjacent_bypass(self):
        paths=[{'points':[[.1,.5],[.9,.5]]},{'points':[[.1,.2],[.9,.2]]}]
        masks=[{'label':'Equipment body','polygon':[[.4,.4],[.6,.4],[.6,.6],[.4,.6]]}]
        parts=rr.clipped_paths(paths,[0,0,1,1],[0,0,1,1],[0,0,1,1],masks)
        self.assertEqual(parts,[[[.1,.5],[.4,.5]],[[.6,.5],[.9,.5]],[[.1,.2],[.9,.2]]])

    def test_overlapping_equipment_masks_remove_shared_body_once(self):
        paths=[{'points':[[.1,.5],[.9,.5]]}]
        masks=[{'polygon':[[.4,.4],[.55,.4],[.55,.6],[.4,.6]]},
               {'polygon':[[.5,.4],[.6,.4],[.6,.6],[.5,.6]]}]
        parts=rr.clipped_paths(paths,[0,0,1,1],[0,0,1,1],[0,0,1,1],masks)
        self.assertAlmostEqual(sum(abs(p[-1][0]-p[0][0]) for p in parts),.6)
        for polygon in ([[0,0],[2,0],[0,1]],[[.1,.1],[.8,.8],[.1,.8],[.8,.1]]):
            with self.assertRaises(ToolError):rr.clipped_paths(paths,[0,0,1,1],[0,0,1,1],[0,0,1,1],[{'polygon':polygon}])

    def test_exclusion_coordinates_are_tile_local_and_boundary_ownership_stays_unique(self):
        crop=[.2,.1,.8,.9];paths=[{'points':[[.5,0],[.5,1]]}]
        masks=[{'polygon':[[.4,.4],[.6,.4],[.6,.6],[.4,.6]]}]
        left=rr.clipped_paths(paths,crop,[.2,.1,.5,.9],crop,masks)
        right=rr.clipped_paths(paths,crop,[.5,.1,.8,.9],crop,masks)
        self.assertEqual(left,[])
        self.assertEqual(len(right),2)
        self.assertAlmostEqual(sum(p[-1][1]-p[0][1] for p in right),.64)

    def test_route_agent_uses_reconciled_source_paths_and_host_math(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unknown.png';image=Image.new('RGB',(1000,600),'white');image.save(path)
            doc={'page_count':1,'pages':[{'page':1,'width':1000,'height':600,'words':[]}],'objects':[]}
            plan={'region':[0,0,1,1],'reference':{'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,.3,.15]},'complete':True,'warnings':[],'reason':'Located source plan'}
            before={'paths':[{'label':'Wrong proposal','points':[[.1,.4],[.9,.4]]}],'complete':True,'warnings':[],'reason':'Proposed'}
            audited={'paths':[{'label':'Actual route','points':[[.1,.4],[.6,.4]]}],'complete':True,'warnings':[],'reason':'Reconciled source'}
            words={'words':[{'text':'10 m','bbox':[.1,.02,.2,.05]}],'complete':True}
            with patch.object(llm,'_request',side_effect=[plan,before,audited]),patch.object(rr,'tile_plan',return_value=iter([([0,0,1,1],[0,0,1,1])])),\
                 patch('server.drawing_tools.DrawingSession._words',return_value=words):
                result=rr.answer('How many metres of pipe length?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
            self.assertAlmostEqual(result['value'],10)
            self.assertEqual(result['unit'],'m')
            self.assertEqual(result['evidence'][0]['polylines'],[[[.1,.4],[.6,.4]]])
            self.assertFalse(result['evidence'][0]['source_verified'])

    def test_equipment_subtraction_is_used_in_the_returned_host_quantity(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unknown.png';Image.new('RGB',(1000,600),'white').save(path)
            doc={'page_count':1,'pages':[{'page':1,'width':1000,'height':600}],'objects':[]}
            plan={'method':'source_geometry','region':[0,0,1,1],
                  'reference':{'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,.3,.15]},
                  'complete':True,'warnings':[],'reason':'Source plan'}
            mask={'label':'Equipment body','polygon':[[.4,.3],[.6,.3],[.6,.5],[.4,.5]]}
            trace={'paths':[{'label':'Pipe','points':[[.1,.4],[.9,.4]]}],'exclusions':[mask],
                   'complete':True,'warnings':[],'reason':'Actual body excludes its interior'}
            words={'words':[{'text':'10 m','bbox':[.1,.02,.2,.05]}],'complete':True}
            with patch.object(llm,'_request',side_effect=[plan,trace,trace]), \
                 patch.object(rr,'tile_plan',return_value=iter([([0,0,1,1],[0,0,1,1])])), \
                 patch('server.drawing_tools.DrawingSession._words',return_value=words):
                result=rr.answer('How many metres of pipe excluding equipment internals?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
            self.assertAlmostEqual(result['value'],12)
            self.assertEqual(len(result['evidence'][0]['polylines']),2)
            self.assertEqual(result['inspection'][0]['equipment_exclusions'],[mask])

    def test_printed_lengths_delegate_instead_of_forcing_scale_and_tracing(self):
        with patch.object(llm,'_request',return_value={'method':'source_annotation','region':None,'reference':None,
            'complete':True,'reason':'A source schedule states the required length','warnings':[]}) as request, \
             patch('server.drawing_tools.fingerprint',return_value='mock-source'), \
             patch('server.rendering.render_region',return_value=Image.new('RGB',(32,32))):
            result=rr.answer('What pipe length is listed in the schedule?',{},Path('unknown.png'),1,'page',[0,0,1,1],model='test',policy={})
            self.assertIsNone(result)
            self.assertEqual(request.call_count,1)

    def test_non_network_length_semantically_delegates_without_pipe_tracing(self):
        with patch.object(llm,'_request',return_value={'method':'source_reader','region':None,'reference':None,
            'complete':True,'reason':'This asks for baseboard along room walls, not a routed service','warnings':[]}) as request, \
             patch('server.drawing_tools.fingerprint',return_value='mock-source'), \
             patch('server.rendering.render_region',return_value=Image.new('RGB',(32,32))):
            self.assertTrue(rr.requested('How many linear metres of baseboard are required?'))
            result=rr.answer('How many linear metres of baseboard are required?',{},Path('unknown.png'),1,'page',[0,0,1,1],model='test',policy={})
            self.assertIsNone(result);self.assertEqual(request.call_count,1)

    def test_closer_coverage_replaces_coarse_trace_and_adds_previously_missed_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unfamiliar.png';Image.new('RGB',(4000,600),'white').save(path)
            doc={'pages':[{'page':1,'width':4000,'height':600}],'objects':[]}
            plan={'method':'source_geometry','region':[0,0,1,1],'complete':True,'warnings':[],
                  'reference':{'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,.3,.15]}}
            coarse={'paths':[{'points':[[.1,.5],[.4,.5]]}],'exclusions':[], 'complete':True}
            closer={'paths':[{'points':[[.2,.5],[.8,.5]]},{'points':[[.5,.5],[.5,.75]]}],
                    'exclusions':[],'complete':True}
            empty={'paths':[],'exclusions':[],'complete':True}
            details=[([0,0,.5,1],[0,0,.5,1]),([.5,0,1,1],[.5,0,1,1])]
            def request(content,**kwargs):
                if kwargs['schema'] is rr.PLAN:return plan
                if 'detail 1/4' in content[0]['text']:return closer
                if 'detail 2/4' in content[0]['text']:return empty
                return coarse
            with patch.object(llm,'_request',side_effect=request), \
                 patch.object(rr,'tile_plan',return_value=iter([([0,0,1,1],[0,0,1,1])])), \
                 patch.object(rr,'coverage_plan',return_value=details), \
                 patch('server.drawing_tools.DrawingSession._words',return_value={'words':[{'text':'10 m','bbox':[.1,.02,.2,.05]}],'complete':True}):
                result=rr.answer('How many metres of pipes?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
            self.assertAlmostEqual(result['value'],6.75)
            self.assertEqual(len(result['evidence'][0]['polylines']),2)
            self.assertEqual(result['route_inspection']['native_detail_regions'],2)

    def test_native_detail_failure_does_not_publish_coarse_total_and_resumes_only_missing_detail(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unfamiliar.png';Image.new('RGB',(4000,600),'white').save(path)
            doc={'pages':[{'page':1,'width':4000,'height':600}],'objects':[]}
            plan={'region':[0,0,1,1],'complete':True,'warnings':[],
                  'reference':{'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,.3,.15]}}
            trace={'paths':[{'points':[[.2,.5],[.8,.5]]}],'exclusions':[],'complete':True}
            details=[([0,0,.5,1],[0,0,.5,1]),([.5,0,1,1],[.5,0,1,1])];failed=[]
            def request(content,**kwargs):
                if kwargs['schema'] is rr.PLAN:return plan
                if 'detail 2/4' in content[0]['text'] and not failed:
                    failed.append(True);raise llm.ModelError('Timed out',recoverable=True)
                return trace
            with patch.object(llm,'_request',side_effect=request) as calls, \
                 patch.object(rr,'tile_plan',side_effect=lambda *a:iter([([0,0,1,1],[0,0,1,1])])), \
                 patch.object(rr,'coverage_plan',return_value=details), \
                 patch('server.drawing_tools.DrawingSession._words',return_value={'words':[{'text':'10 m','bbox':[.1,.02,.2,.05]}],'complete':True}):
                first=rr.answer('How many metres of pipes?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
                second=rr.answer('How many metres of pipes?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
            self.assertIsNone(first['value']);self.assertTrue(first['retryable_analysis'])
            self.assertEqual(first['route_inspection']['retryable_regions'],1)
            self.assertAlmostEqual(second['value'],12)
            self.assertEqual(second['route_inspection']['cached_tiles'],1)
            self.assertEqual(calls.call_count,6)

    def test_unavailable_vertical_or_offsheet_scope_is_not_replaced_by_visible_length(self):
        with patch.object(llm,'_request',return_value={'complete':False,'reason':'Referenced vertical runs are missing.'}),\
             patch('server.drawing_tools.fingerprint',return_value='mock-source'),\
             patch('server.rendering.render_region',return_value=Image.new('RGB',(32,32))):
            result=rr.answer('How many metres of pipes including all vertical runs?',{},Path('x.png'),1,'document',[0,0,1,1],model='test',policy={})
        self.assertIsNone(result['value']);self.assertIn('vertical',result['answer'])

    def test_transient_region_failure_retains_evidence_and_retry_resumes_only_missing_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unknown.png';Image.new('RGB',(1000,600),'white').save(path)
            doc={'page_count':1,'pages':[{'page':1,'width':1000,'height':600}],'objects':[]}
            plan={'region':[0,0,1,1],'reference':{'points':[[.1,.2],[.6,.2]],'value':10,
                'unit':'m','quote':'10 m','annotation_bbox':[.05,0,.3,.15]},'complete':True,'warnings':[],'reason':'Source scale'}
            traced={'paths':[{'label':'Route','points':[[.2,.5],[.8,.5]]}],
                    'complete':True,'warnings':[],'reason':'Reviewed source'}
            failed=[]
            def request(content,**kwargs):
                if kwargs['schema'] is rr.PLAN:return plan
                if 'Tile 1/2' in content[0]['text'] and not failed:
                    failed.append(True);raise llm.ModelError('Read timed out',recoverable=True)
                return traced
            tiles=[([0,0,.5,1],[0,0,.5,1]),([.5,0,1,1],[.5,0,1,1])]
            words={'words':[{'text':'10 m','bbox':[.1,.02,.2,.05]}],'complete':True}
            with patch.object(llm,'_request',side_effect=request) as calls,\
                 patch.object(rr,'tile_plan',side_effect=lambda *a:iter(tiles)),\
                 patch('server.drawing_tools.DrawingSession._words',return_value=words):
                first=rr.answer('How many metres of pipes?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
                self.assertIsNone(first['value']);self.assertEqual(len(first['evidence']),1)
                self.assertEqual(first['route_inspection']['retryable_regions'],1)
                second=rr.answer('How many metres of pipes?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
            self.assertAlmostEqual(second['value'],12)
            self.assertEqual(second['route_inspection']['cached_tiles'],1)
            self.assertTrue(second['route_inspection']['plan_cache_hit'])
            self.assertEqual(calls.call_count,6)

    def test_calibration_retry_sees_positioned_source_words_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unknown.png';Image.new('RGB',(1000,600),'white').save(path)
            doc={'page_count':1,'pages':[{'page':1,'width':1000,'height':600}],'objects':[]}
            plan={'region':[0,0,1,1],'reference':{'points':[[.1,.2],[.6,.2]],
                  'value':10,'unit':'m','quote':'10 m','annotation_bbox':[.1,.02,.3,.1]},
                  'complete':True,'warnings':[],'reason':'Located source'}
            words={'words':[{'text':'10 m','bbox':[.1,.02,.2,.05]}],'complete':True}
            empty={'paths':[],'complete':False,'warnings':[],'reason':'Unresolved pipe route'}
            execute=rr.DrawingSession.execute;attempts=[]
            def calibration(session,request):
                if request['name']=='calibrate':
                    attempts.append(request)
                    if len(attempts)==1:raise ToolError('Source quote mismatch')
                return execute(session,request)
            with patch.object(llm,'_request',side_effect=[plan,plan,empty,empty]) as request,\
                 patch.object(rr.DrawingSession,'execute',calibration),\
                 patch('server.drawing_tools.read_words',return_value=words),\
                 patch.object(rr,'tile_plan',return_value=iter([([0,0,1,1],[0,0,1,1])])):
                result=rr.answer('How many metres of pipes?',doc,path,1,'page',[0,0,1,1],model='test',policy={})
            correction=request.call_args_list[1].args[0]
            self.assertTrue(any('Fallible positioned source OCR' in c.get('text','') and '10 m' in c['text'] for c in correction))
            self.assertIsNone(result['value'])
            self.assertEqual(result['inspection'][0]['stage'],'source_calibration')


if __name__=='__main__':unittest.main()
