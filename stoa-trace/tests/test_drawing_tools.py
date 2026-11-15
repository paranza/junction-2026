import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

from server import drawing_tools as dt, deep_reader


class SourceTools(unittest.TestCase):
    def test_ocr_deduplication_preserves_imperial_units_and_normalizes_prime_glyphs(self):
        def word(text,confidence):return {'text':text,'confidence':confidence,'bbox':[.1,.1,.2,.2]}
        result=dt.deduplicate_words([word('8',.999),word("8'",.9),word('8′',.8),word('8"',.7)])
        self.assertEqual({r['text'] for r in result},{'8',"8'",'8"'})

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'drawing.png'
        self.image=Image.new('RGB',(1000,600),'white');self.image.save(self.path)
        self.session=dt.DrawingSession(self.path,1,[0,0,1,1])

    def calibrated(self):
        words={'words':[{'text':'10 m','bbox':[.1,.05,.2,.1],'confidence':.99}], 'complete':True}
        with patch.object(self.session,'_words',return_value=words):
            return self.session.execute({'name':'calibrate','region':[0,0,1,1],
                'reference':{'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[.05,0,.3,.15]}})

    def test_concave_area_and_diagonal_polyline_use_aspect_and_source_scale(self):
        cal=self.calibrated()
        result=self.session.execute({'name':'polygon','calibration_id':cal['id'],
            'geometry':[[.1,.2],[.6,.2],[.6,.4],[.3,.4],[.3,.7],[.1,.7]]})
        # Concave polygon: 500*120 + 200*180 pixels, at .02 metres/pixel.
        self.assertAlmostEqual(result['value'],38.4,places=5)
        path=self.session.execute({'name':'path','calibration_id':cal['id'],
            'geometry':[[.1,.2],[.6,.2],[.6,.7]]})
        self.assertAlmostEqual(path['value'],16,places=5)
        self.assertEqual(self.session.operand(path['id'])['polyline'],path['geometry'])
        self.assertFalse(result['source_verified'])

    def test_closed_perimeter_and_disconnected_paths_do_not_count_gaps_or_shared_edges(self):
        cal=self.calibrated()
        outline=[[.1,.2],[.6,.2],[.6,.7],[.1,.7]]
        perimeter=self.session.execute({'name':'perimeter','calibration_id':cal['id'],'geometry':outline})
        self.assertAlmostEqual(perimeter['value'],32)
        self.assertEqual(perimeter['geometry'][0],perimeter['geometry'][-1])
        measured=self.session.execute({'name':'multipath','calibration_id':cal['id'],
            'geometry':[[.1,.2],[.6,.2],None,[.3,.2],[.6,.2],None,[.6,.3],[.6,.7]]})
        self.assertAlmostEqual(measured['value'],14.8)
        self.assertEqual(len(self.session.operand(measured['id'])['polylines']),3)
        preview,region=self.session.preview(measured['id'])
        self.assertGreater(preview.width,0)
        self.assertLessEqual(region[0],.1)
        _,detail=self.session.preview(measured['id'],part=measured['polylines'][-1])
        self.assertGreater(detail[0],region[0])
        self.assertLess(detail[2]-detail[0],region[2]-region[0])
        with self.assertRaises(dt.ToolError):self.session.preview(measured['id'],part=[[0,0],[1,1]])

    def test_fabricated_reference_and_scope_escape_rejected(self):
        with patch.object(self.session,'_words',return_value={'words':[],'complete':True}):
            with self.assertRaises(dt.ToolError):self.calibrated_unmocked()
        session=dt.DrawingSession(self.path,1,[.1,.1,.6,.6])
        with self.assertRaises(dt.ToolError):session.execute({'name':'ocr','region':[0,0,1,1]})
        self.calibrated()
        with self.assertRaises(dt.ToolError):self.session.execute({'name':'polygon','calibration_id':'t999','geometry':[[.1,.2],[.3,.2],[.3,.5]]})

    def calibrated_unmocked(self):
        return self.session.execute({'name':'calibrate','reference':{'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,.3,.2]}})

    def test_calibration_retains_unit_suffix_from_the_same_located_token(self):
        words={'words':[{'text':"8'",'bbox':[.1,.05,.2,.1]}],'complete':True}
        with patch.object(self.session,'_words',return_value=words):
            result=self.session.execute({'name':'calibrate','reference':{
                'points':[[.1,.2],[.6,.2]],'value':8,'unit':'ft','quote':'8','annotation_bbox':[0,0,.3,.2]}})
        self.assertEqual(result['reference']['quote'],"8'")

    def test_scale_context_recovers_prime_without_borrowing_a_nearby_quantity(self):
        reference={'points':[[.1,.2],[.6,.2]],'value':8,'unit':'ft',
                   'quote':"0 2' 4' 8'",'annotation_bbox':[.1,.02,.3,.1]}
        original=reference['annotation_bbox']
        def words(region):
            return {'complete':True,'words':[{'text':'8','bbox':[.2,.04,.23,.07]}] if region==original else
                [{'text':"8'",'bbox':[.2,.04,.23,.07]}]}
        with patch.object(self.session,'_words',side_effect=words):
            result=self.session.execute({'name':'calibrate','reference':reference})
        self.assertEqual(result['reference']['quote'],"8'")
        # A matching dimension from outside the original located scale label
        # must not be borrowed even if visible in the wider OCR context.
        other=dt.DrawingSession(self.path,1,[0,0,1,1])
        with patch.object(other,'_words',return_value={'complete':True,'words':[
                {'text':"8'",'bbox':[.4,.04,.45,.07]}]}):
            with self.assertRaises(dt.ToolError):other.execute({'name':'calibrate','reference':reference})
        self.assertAlmostEqual(self.session.calibrations[result['id']]['metres'],2.4384)
        self.assertFalse(result['source_verified'])

    def test_calibration_does_not_take_units_from_another_token_or_wrong_value(self):
        for texts in (['8','ft'],['8 m'],["18'"],['8']):
            words={'words':[{'text':t,'bbox':[.1,.05,.2,.1]} for t in texts],'complete':True}
            with self.subTest(texts=texts),patch.object(self.session,'_words',return_value=words):
                with self.assertRaises(dt.ToolError):
                    self.session.execute({'name':'calibrate','reference':{
                        'points':[[.1,.2],[.6,.2]],'value':8,'unit':'ft','quote':'8','annotation_bbox':[0,0,.3,.2]}})

    def test_source_change_invalidates_tools(self):
        self.calibrated();self.image.resize((800,600)).save(self.path)
        with self.assertRaises(dt.ToolError):self.session.execute({'name':'ocr'})

    def test_reference_outside_selection_does_not_expand_quantity_scope(self):
        self.session=dt.DrawingSession(self.path,1,[.1,.3,.7,.8]);cal=self.calibrated()
        result=self.session.execute({'name':'path','calibration_id':cal['id'],'region':[.1,.3,.7,.8],
            'geometry':[[.2,.4],[.6,.4]]})
        self.assertAlmostEqual(result['value'],8)
        with self.assertRaises(dt.ToolError):self.session.execute({'name':'path','calibration_id':cal['id'],
            'region':[.1,.3,.7,.8],'geometry':[[.2,.4],[.9,.4]]})

    def test_area_evidence_retains_actual_polygon_and_focus_bounds(self):
        cal=self.calibrated();geometry=[[.1,.2],[.6,.2],[.6,.7],[.1,.7]]
        result=self.session.execute({'name':'polygon','calibration_id':cal['id'],'geometry':geometry})
        operand=self.session.operand(result['id'])
        self.assertEqual(operand['polygon'],geometry)
        self.assertLess(operand['bbox'][2]-.6,.001)

    def test_self_crossing_polygon_and_unclosed_room_rejected(self):
        cal=self.calibrated()
        with self.assertRaises(dt.ToolError):self.session.execute({'name':'polygon','calibration_id':cal['id'],
            'geometry':[[.1,.2],[.6,.7],[.6,.2],[.1,.7]]})
        with self.assertRaises(dt.ToolError):self.session.execute({'name':'room','calibration_id':cal['id'],'seed':[.4,.4]})

    def test_closed_room_recovers_source_geometry(self):
        draw=ImageDraw.Draw(self.image);draw.rectangle((100,150,600,450),outline='black',width=3);self.image.save(self.path)
        self.session=dt.DrawingSession(self.path,1,[0,0,1,1]);cal=self.calibrated()
        result=self.session.execute({'name':'room','calibration_id':cal['id'],'seed':[.4,.5]})
        self.assertAlmostEqual(result['value'],60,delta=2)
        self.assertGreater(len(result['geometry']),3)

    def test_template_proposals_exclude_legend_and_remain_incomplete(self):
        draw=ImageDraw.Draw(self.image)
        for x in (100,400,700):
            draw.polygon([(x,100),(x+30,120),(x,140),(x+30,100),(x+30,140)],outline='black',width=3)
        self.image.save(self.path);self.session=dt.DrawingSession(self.path,1,[0,0,1,1])
        result=self.session.execute({'name':'symbols','region':[0,0,1,1],'template':[.095,.155,.135,.245]})
        self.assertGreaterEqual(len(result['matches']),2)
        self.assertFalse(result['complete']);self.assertIsNone(self.session.operand(result['id']))

    def test_tool_operand_overrides_model_numbers_and_cannot_be_forged(self):
        cal=self.calibrated();fact=self.session.execute({'name':'path','calibration_id':cal['id'],'geometry':[[.1,.2],[.6,.2]]})
        raw={'operation':'length','unit':'m','complete':True,'expression':'e0','warnings':[],
             'evidence':[{'tool_id':fact['id'],'value':999,'unit':'km','label':'Selected run'}]}
        inputs=[{'image':self.image,'page':1,'region':[0,0,1,1]}]
        result=deep_reader.finalize(raw,inputs,{},'What is the length?',[0,0,1,1],[],self.session)
        self.assertAlmostEqual(result['value'],10)
        raw['evidence'][0]['tool_id']='t999'
        self.assertIsNone(deep_reader.finalize(raw,inputs,{},'What is the length?',[0,0,1,1],[],self.session)['value'])

    def test_agent_can_calibrate_measure_and_answer_with_host_operands(self):
        import os
        from server import llm
        reference={'points':[[.1,.2],[.6,.2]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[.05,0,.3,.15]}
        decisions=[{'action':'tool','tools':[{'name':'calibrate','reference':reference}]},
                   {'action':'tool','tools':[{'name':'path','calibration_id':'t1','geometry':[[.1,.2],[.6,.2],[.6,.7]]}]},
                   {'action':'answer','result':{'operation':'length','complete':True,'unit':'m','expression':'e0','warnings':[],
                     'evidence':[{'tool_id':'t2','label':'Run','value':999,'unit':'km'}]}}]
        with patch.dict(os.environ,{'STOA_COMPLEX_READER':'auto','STOA_ROUTE_READER':'off'}),patch.object(llm,'PROVIDER','gemini'),\
             patch.object(llm,'_request',side_effect=decisions) as request,\
             patch.object(dt.DrawingSession,'_words',return_value={'words':[{'text':'10 m'}],'complete':True}):
            result=deep_reader.answer('What is the length?',{'page_count':1,'pages':[{'page':1,'width':6000,'height':4000}]},self.path,region=[0,0,1,1])
        self.assertAlmostEqual(result['value'],16)
        self.assertEqual(request.call_count,3)
        self.assertFalse(result['evidence'][0]['source_verified'])

    def test_rotated_pdf_native_words_and_original_vectors(self):
        import pymupdf
        path=Path(self.directory.name)/'rotated.pdf'
        doc=pymupdf.open();p=doc.new_page(width=600,height=400)
        p.insert_text((40,50),'Reference 10 m and enough native words to read a source drawing without OCR')
        p.draw_line((100,100),(400,100));p.set_rotation(90);doc.save(path);doc.close()
        words=dt._native_words(path,1)
        self.assertTrue(any(w['text']=='Reference' for w in words))
        self.assertTrue(all(0<=v<=1 for w in words for v in w['bbox']))
        session=dt.DrawingSession(path,1,[0,0,1,1])
        with patch.object(session,'_words',return_value={'words':[{'text':'10 m'}],'complete':True}):
            cal=session.execute({'name':'calibrate','reference':{'points':[[.75,1/6],[.75,4/6]],'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,1,1]}})
        result=session.execute({'name':'vectors','calibration_id':cal['id']})
        self.assertEqual(len(result['segments']),1)
        self.assertAlmostEqual(result['segments'][0]['value'],10,delta=.02)
        self.assertIsNone(session.operand(result['id']))
        self.assertIsNotNone(session.operand(result['segments'][0]['id']))


class LineGraph(unittest.TestCase):
    def test_branches_not_double_counted_and_seed_excludes_other_component(self):
        mask=np.zeros((120,220),bool);mask[50,10:111]=1;mask[20:81,60]=1
        mask[100,150:201]=1
        result=dt.skeleton_graph(mask,[15,50])
        self.assertAlmostEqual(result['length_pixels'],160)
        self.assertEqual(result['endpoints'],4)
        self.assertEqual(result['junctions'],1)
        self.assertAlmostEqual(dt.skeleton_graph(mask)['length_pixels'],210)

    def test_closed_loop_is_measured_once(self):
        mask=np.zeros((90,90),bool);mask[20,20:61]=1;mask[60,20:61]=1;mask[20:61,20]=1;mask[20:61,60]=1
        self.assertAlmostEqual(dt.skeleton_graph(mask)['length_pixels'],160)

    def test_too_distant_seed_and_empty_graph_fail(self):
        mask=np.zeros((90,90),bool);mask[20,20:61]=1
        with self.assertRaises(dt.ToolError):dt.skeleton_graph(mask,[80,80])
        with self.assertRaises(dt.ToolError):dt.skeleton_graph(np.zeros((10,10),bool))


class PositionedOCR(unittest.TestCase):
    def test_cache_reused_content_addressed_and_native_coordinates_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.png';Image.new('RGB',(600,400),'white').save(path)
            fake=[([[20,30],[120,30],[120,50],[20,50]],'12 m',.99)]
            with patch.object(dt,'_engine_read',return_value=fake) as engine:
                first=dt.read_words(path,1,[0,0,1,1],cache_root=Path(directory)/'cache',rotated=False)
                second=dt.read_words(path,1,[0,0,1,1],cache_root=Path(directory)/'cache',rotated=False)
                self.assertEqual(engine.call_count,1)
            self.assertEqual(first,second);self.assertAlmostEqual(first['words'][0]['bbox'][0],20/600)
            self.assertEqual(first['words'][0]['text'],'12 m')

    def test_rotated_ocr_maps_back_to_original_page(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.png';Image.new('RGB',(600,400),'white').save(path)
            with patch.object(dt,'_engine_read',side_effect=[[],[([[30,100],[50,100],[50,200],[30,200]],'Valve',.99)]]):
                result=dt.read_words(path,1,[0,0,1,1],cache_root=Path(directory)/'cache')
            self.assertAlmostEqual(result['words'][0]['bbox'][0],400/600)
            self.assertAlmostEqual(result['words'][0]['bbox'][2],500/600)

    def test_overlap_duplicate_text_is_removed_but_distinct_locations_retained(self):
        rows=[{'text':'FSR-1','bbox':[.1,.1,.2,.2],'confidence':.9},
              {'text':'FSR-1','bbox':[.11,.1,.21,.2],'confidence':.8},
              {'text':'FSR-1','bbox':[.6,.1,.7,.2],'confidence':.8}]
        self.assertEqual(len(dt.deduplicate_words(rows)),2)


if __name__=='__main__':unittest.main()
