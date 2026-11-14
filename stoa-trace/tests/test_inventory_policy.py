"""Reading budgets and tiled local detections preserve source coordinates and base answers."""
import hashlib
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from server import detector,inventory,llm
from tests import test_backend_upgrade as fixture


class ReadingPolicy(unittest.TestCase):
    setUp=fixture.BackendUpgrade.setUp
    tearDown=fixture.BackendUpgrade.tearDown
    def response(self,ambiguous=False,count=1):
        return {'complete':True,'warnings':[],'objects':[
            {'category':'window','label':'Window','image_index':0,'bbox':[.1+i*.2,.1,.2+i*.2,.2],'ambiguous':ambiguous} for i in range(count)]}
    def run_inventory(self,responses,**settings):
        with patch.dict(os.environ,{'STOA_INVENTORY_POLICY':'adaptive','STOA_SYMBOL_READER':'standard','STOA_INVENTORY_FALLBACK_MODEL':'',**settings}),\
             patch.object(inventory,'READINGS',2),patch.object(detector,'signature',return_value=None),\
             patch.object(inventory,'image_inputs',return_value=self.images),patch.object(llm,'_request',side_effect=responses) as request:
            result=inventory.page_inventory(self.native,self.path,1)
            return result,request.call_count
    def test_one_larger_model_fallback_only_after_all_retryable_failures(self):
        response=self.response();response['_model']='gemini-4-argon'
        with patch.object(llm,'PROVIDER','gemini'),patch.object(llm,'MODEL','gemini-4-carbon'):
            result,calls=self.run_inventory([llm.ModelError('Incomplete',recoverable=True),llm.ModelError('Transport timeout',recoverable=True),response],
                STOA_INVENTORY_POLICY='repeat',STOA_INVENTORY_FALLBACK_MODEL='gemini-4-argon')
        self.assertEqual(calls,3);self.assertEqual(result['model'],'gemini-4-argon')
        self.assertEqual(result['reading_policy']['failure_fallback_model'],'gemini-4-argon')
        self.assertEqual(result['reading_policy']['attempts'],3)
        self.assertEqual(len(result['objects']),1)
    def test_authentication_failure_never_triggers_fallback(self):
        with patch.object(llm,'PROVIDER','gemini'),patch.object(llm,'MODEL','gemini-4-carbon'):
            with self.assertRaisesRegex(llm.ModelError,'authentication'):
                self.run_inventory([llm.ModelError('authentication'),llm.ModelError('authentication')],
                    STOA_INVENTORY_POLICY='repeat',STOA_INVENTORY_FALLBACK_MODEL='gemini-4-argon')
    def test_successful_primary_reading_is_never_replaced(self):
        with patch.object(llm,'PROVIDER','gemini'),patch.object(llm,'MODEL','gemini-4-carbon'):
            result,calls=self.run_inventory([self.response(),self.response(count=2)],
                STOA_INVENTORY_POLICY='repeat',STOA_INVENTORY_FALLBACK_MODEL='gemini-4-argon')
        self.assertEqual(calls,2);self.assertEqual(len(result['objects']),1)
    def test_real_request_ledger_counts_failed_readings_and_recovery(self):
        usage={'input_tokens':10,'output_tokens':20,'input_tokens_details':{'cached_tokens':0}}
        incomplete={'status':'incomplete','usage':usage,'output':[]}
        complete={'status':'completed','usage':usage,'output':[{'content':[{'type':'output_text','text':json.dumps(self.response())}]}]}
        with patch.dict(os.environ,{'STOA_INVENTORY_POLICY':'repeat','STOA_INVENTORY_FALLBACK_MODEL':'gemini-4-argon'}),\
             patch.object(llm,'PROVIDER','gemini'),patch.object(llm,'MODEL','gemini-4-carbon'),patch.object(llm,'KEY','test-key'),patch.object(llm,'MAX_CALLS',3),\
             patch.object(inventory,'READINGS',2),patch.object(inventory,'image_inputs',return_value=self.images),patch.object(detector,'signature',return_value=None),\
             patch.object(llm.gemini_provider,'request',side_effect=[incomplete,incomplete,complete]),llm.usage_scope():
            result=inventory.page_inventory(self.native,self.path,1)
            usage=llm.usage_snapshot()
        self.assertEqual(usage['model_calls'],3);self.assertEqual(usage['input_tokens'],30)
        self.assertEqual(usage['output_tokens'],60);self.assertEqual(result['ingestion_usage']['model_calls'],3)
        with llm.store.connection() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE kind='model_request'").fetchone()[0],3)
    def test_recovery_cannot_exceed_persisted_attempt_ceiling(self):
        incomplete={'status':'incomplete','usage':None,'output':[]}
        with patch.dict(os.environ,{'STOA_INVENTORY_POLICY':'repeat','STOA_INVENTORY_FALLBACK_MODEL':'gemini-4-argon'}),\
             patch.object(llm,'PROVIDER','gemini'),patch.object(llm,'MODEL','gemini-4-carbon'),patch.object(llm,'KEY','test-key'),patch.object(llm,'MAX_CALLS',2),\
             patch.object(inventory,'READINGS',2),patch.object(inventory,'image_inputs',return_value=self.images),patch.object(detector,'signature',return_value=None),\
             patch.object(llm.gemini_provider,'request',return_value=incomplete) as request,llm.usage_scope():
            with self.assertRaisesRegex(llm.ModelError,'allowance'):inventory.page_inventory(self.native,self.path,1)
        self.assertEqual(request.call_count,2)
        with llm.store.connection() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE kind='model_request'").fetchone()[0],2)
    def test_adaptive_skips_repeat_for_clean_first_reading(self):
        result,calls=self.run_inventory([self.response()])
        self.assertEqual(calls,1)
        self.assertEqual(result['reading_policy']['attempts'],1)
        self.assertEqual(len(result['objects']),1)
    def test_repeat_flag_does_not_replace_first_count(self):
        result,calls=self.run_inventory([self.response(ambiguous=True),self.response(count=2)])
        self.assertEqual(calls,2)
        self.assertEqual(len(result['objects']),1)
        self.assertEqual(len(result['other_readings'][0]['objects']),2)
    def test_first_failure_uses_remaining_allowance(self):
        result,calls=self.run_inventory([llm.ModelError('Temporary failure'),self.response()])
        self.assertEqual((calls,len(result['objects'])),(2,1))
    def test_explicit_repeat_policy_keeps_configured_readings(self):
        result,calls=self.run_inventory([self.response(),self.response()],STOA_INVENTORY_POLICY='repeat')
        self.assertEqual(calls,2)
    def test_focused_reader_has_a_separate_schema_and_cache(self):
        with patch.dict(os.environ,{'STOA_INVENTORY_POLICY':'repeat','STOA_SYMBOL_READER':'standard'}),\
             patch.object(inventory,'image_inputs',return_value=self.images),patch.object(llm,'_request',return_value=self.response()) as request:
            inventory.page_inventory(self.native,self.path,1)
            inventory.page_inventory(self.native,self.path,1,focus_categories=('window',))
            self.assertEqual(request.call_count,2)
            self.assertEqual(request.call_args.kwargs['schema']['properties']['objects']['items']['properties']['category']['enum'],['window'])


class LocalDetector(unittest.TestCase):
    def test_tiled_boxes_own_centers_and_preserve_source_coordinates(self):
        import numpy as np
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);(folder/'model.onnx').write_bytes(b'tiled-fixture')
            manifest={'kind':'yolo_boxes','model_file':'model.onnx','model_sha256':hashlib.sha256(b'tiled-fixture').hexdigest(),
                      'classes':['door','window'],'input_size':320,'inference_mode':'native_tiles'}
            path=folder/'manifest.json';path.write_text(json.dumps(manifest))
            class Session:
                def get_inputs(self):return [type('Input',(),{'name':'images'})()]
                def run(self,_,inputs):
                    points=np.argwhere(inputs['images'][0,0]<.01)
                    output=np.zeros((1,6,max(1,len(points))),np.float32)
                    for i,(y,x) in enumerate(points):output[0,:,i]=[x,y,2,2,0,1]
                    return [output]
            image=Image.new('RGB',(600,200),'white');image.putpixel((159,100),(0,0,0));image.putpixel((162,100),(0,0,0))
            with patch.dict(os.environ,{'STOA_DETECTOR_MANIFEST':str(path)}),patch.object(detector,'_session',return_value=Session()):
                result=detector.detect_image(image,document_id='source-a',page=3)
                other=detector.detect_image(image,document_id='source-b',page=3)
            self.assertFalse(result.get('unavailable'));self.assertEqual(len(result['objects']),2)
            self.assertEqual(result['inference_mode'],'native_tiles')
            self.assertAlmostEqual(result['objects'][0]['point'][0],159/600)
            self.assertAlmostEqual(result['objects'][1]['point'][0],162/600)
            self.assertTrue(set(o['id'] for o in result['objects']).isdisjoint(o['id'] for o in other['objects']))
    def test_box_detector_maps_letterbox_and_deduplicates(self):
        import numpy as np
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);(folder/'model.onnx').write_bytes(b'box-fixture')
            manifest={'kind':'yolo_boxes','model_file':'model.onnx','model_sha256':hashlib.sha256(b'box-fixture').hexdigest(),
                      'classes':['door','window'],'input_size':640,'class_thresholds':{'door':.4,'window':.5}}
            path=folder/'manifest.json';path.write_text(json.dumps(manifest))
            class Session:
                def get_inputs(self):return [type('Input',(),{'name':'images'})()]
                def run(self,_,inputs):
                    self.shape=inputs['images'].shape
                    self.center=inputs['images'][0,:,320,320]
                    return [np.array([[[320,322,512,200],[320,320,320,30],[128,128,64,30],[64,64,64,20],[.9,.8,.02,.7],[.02,.02,.85,.01]]],np.float32)]
            session=Session()
            with patch.dict(os.environ,{'STOA_DETECTOR_MANIFEST':str(path)}),patch.object(detector,'_session',return_value=session):
                result=detector.detect_image(Image.new('RGB',(400,200),'white'),document_id='source',page=2)
            self.assertFalse(result.get('unavailable'));self.assertEqual(session.shape,(1,3,640,640))
            self.assertEqual([o['category'] for o in result['objects']],['door','window'])
            for actual,expected in zip(result['objects'][0]['bbox'],[.4,.4,.6,.6]):self.assertAlmostEqual(actual,expected,places=6)
            self.assertTrue(all(o['page']==2 and not o['source_verified'] for o in result['objects']))
            manifest['color_mode']='grayscale';path.write_text(json.dumps(manifest))
            with patch.dict(os.environ,{'STOA_DETECTOR_MANIFEST':str(path)}),patch.object(detector,'_session',return_value=session):
                detector.detect_image(Image.new('RGB',(400,200),'red'))
                self.assertEqual(detector.signature()['color_mode'],'grayscale')
            self.assertTrue(np.allclose(session.center,76/255))
    def test_unconfigured_model_does_not_need_runtime_dependencies(self):
        with patch.dict(os.environ,{'STOA_DETECTOR_MANIFEST':''}):
            self.assertIsNone(detector.signature())
            self.assertIsNone(detector.detect_image(Image.new('L',(20,20))))
    def test_tile_ownership_and_normalized_centers(self):
        import numpy as np
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);(folder/'model.onnx').write_bytes(b'model-fixture')
            manifest={'kind':'plannet_heatmap','model_file':'model.onnx',
                      'model_sha256':hashlib.sha256(b'model-fixture').hexdigest(),'classes':['door','window']}
            path=folder/'manifest.json';path.write_text(json.dumps(manifest))
            class Session:
                def get_inputs(self):return [type('Input',(),{'name':'ink'})()]
                def run(self,_,inputs):
                    output=np.zeros((1,2,640,640),np.float32)
                    output[0,1]=inputs['ink'][0,0]
                    return [output]
            image=Image.new('L',(700,300),255);image.putpixel((511,90),0);image.putpixel((600,120),0)
            with patch.dict(os.environ,{'STOA_DETECTOR_MANIFEST':str(path)}),patch.object(detector,'_session',return_value=Session()):
                result=detector.detect_image(image,document_id='drawing',page=3)
            self.assertFalse(result.get('unavailable'))
            self.assertEqual(len(result['objects']),2)
            self.assertEqual(result['objects'][0]['page'],3)
            self.assertAlmostEqual(result['objects'][0]['point'][0],511/700)
            self.assertTrue(all(o['extent_estimated'] and not o['source_verified'] for o in result['objects']))
            manifest['model_sha256']='bad';path.write_text(json.dumps(manifest))
            with patch.dict(os.environ,{'STOA_DETECTOR_MANIFEST':str(path)}):
                self.assertTrue(detector.signature()['unavailable'])
                self.assertTrue(detector.detect_image(image)['unavailable'])


if __name__=='__main__':unittest.main()
