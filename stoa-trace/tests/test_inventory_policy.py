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
        with patch.dict(os.environ,{'STOA_INVENTORY_POLICY':'adaptive','STOA_SYMBOL_READER':'standard',**settings}),\
             patch.object(inventory,'READINGS',2),patch.object(detector,'signature',return_value=None),\
             patch.object(inventory,'image_inputs',return_value=self.images),patch.object(llm,'_request',side_effect=responses) as request:
            result=inventory.page_inventory(self.native,self.path,1)
            return result,request.call_count
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
