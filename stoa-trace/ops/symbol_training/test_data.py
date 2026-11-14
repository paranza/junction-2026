"""Annotation-coordinate regression checks in the separate training environment."""
import json,tempfile,unittest
from pathlib import Path
from PIL import Image
from data import load_sample
from prepare_yolo import prepare
class SourceCoordinates(unittest.TestCase):
 def test_svg_artboard_does_not_rescale_raster_annotations(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);sample=root/'train/example';sample.mkdir(parents=True)
   Image.new('RGB',(32,24),'red').save(sample/'F1_scaled.png')
   (sample/'model.svg').write_text('<svg viewBox="0 0 320 240"><g id="Door"><polygon points="4,6 12,6 12,18 4,18"/></g><g id="Window"><polygon points="40,3 45,3 45,8 40,8"/></g></svg>')
   image,objects=load_sample(root,'train/example')
   self.assertEqual(image.size,(32,24));self.assertEqual(objects,[{'category':0,'bbox':[4,6,12,18]}])
   selection={'train':['train/example'],'validation':[],'confirmation':['not-present'],'source':'test source','license':'test fixture'}
   (root/'selection.json').write_text(json.dumps(selection))
   export=root/'export';prepare(root,export)
   labels=list((export/'labels/train').glob('*.txt'))
   self.assertEqual(len(labels),1)
   values=labels[0].read_text().split();self.assertEqual(values[0],'0')
   self.assertEqual([float(v) for v in values[1:]],[.25,.5,.25,.5])
   self.assertFalse((export/'images/test').exists())
   self.assertFalse(json.loads((export/'provenance.json').read_text())['confirmation_exported'])
   rgb_export=root/'rgb-export';prepare(root,rgb_export,rgb=True)
   with Image.open(next((rgb_export/'images/train').glob('*.png'))) as source:
    self.assertEqual(source.getpixel((0,0)),(255,0,0))
   self.assertEqual(json.loads((rgb_export/'provenance.json').read_text())['color_mode'],'rgb')
if __name__=='__main__':unittest.main()
