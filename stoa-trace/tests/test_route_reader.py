from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from PIL import Image
from server import route_reader as rr,llm
from server.drawing_tools import ToolError


class SourceRouteTakeoff(unittest.TestCase):
    def test_intent_is_length_not_nominal_diameter_or_hidden_quantity_substitution(self):
        self.assertTrue(rr.requested('How many metres of pipe centreline are drawn?'))
        self.assertTrue(rr.requested('Quanti metri di tubi ci sono nel progetto?'))
        self.assertTrue(rr.requested('How many feet of pipe are actually drawn?'))
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

    def test_unavailable_vertical_or_offsheet_scope_is_not_replaced_by_visible_length(self):
        with patch.object(llm,'_request',return_value={'complete':False,'reason':'Referenced vertical runs are missing.'}),\
             patch('server.rendering.render_region',return_value=Image.new('RGB',(32,32))):
            result=rr.answer('How many metres of pipes including all vertical runs?',{},Path('x.png'),1,'document',[0,0,1,1],model='test',policy={})
        self.assertIsNone(result['value']);self.assertIn('vertical',result['answer'])

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
