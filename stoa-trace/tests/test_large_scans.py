"""Large engineering scans retain source pixels when a user selects a region."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw
from server import rendering,native_worker

class LargeEngineeringScan(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  cls.path=cls.root/'independent-large-scan.png'
  image=Image.new('1',(12500,10000),1);draw=ImageDraw.Draw(image)
  for x in range(10000,10100,2):draw.line((x,7000,x,7099),fill=0,width=1)
  image.save(cls.path)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_original_dimensions_and_bounded_isolated_preview(self):
  pages,_=rendering.raster_metadata(self.path)
  self.assertEqual((pages[0]['width'],pages[0]['height']),(12500,10000))
  with patch.object(native_worker,'call',wraps=native_worker.call) as worker:
   image,path=rendering.render_page(self.path,1,600)
  self.assertEqual(image.size,(600,480));self.assertEqual(image.mode,'RGB')
  self.assertEqual(path.resolve(),self.path.resolve());self.assertEqual(worker.call_args.args[0],'render')
 def test_selection_crops_original_pixels_instead_of_the_overview(self):
  region=[.8,.7,.808,.71]
  with patch.object(native_worker,'call',wraps=native_worker.call) as worker:
   inputs=rendering.image_inputs(self.path,[1],region)
  image=inputs[0]['image']
  self.assertEqual(image.size,(100,100));self.assertEqual(inputs[0]['region'],region)
  self.assertEqual(image.getpixel((20,50)),(0,0,0));self.assertEqual(image.getpixel((21,50)),(255,255,255))
  self.assertEqual(worker.call_args.args[0],'raster_region')
 def test_source_pixel_limit_remains_enforced_before_decode(self):
  with patch.object(rendering,'MAX_RASTER_PIXELS',120_000_000):
   with self.assertRaisesRegex(ValueError,'pixel limit'):rendering.raster_metadata(self.path)

class OrientedRegion(unittest.TestCase):
 def test_selected_coordinates_follow_the_oriented_page(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'camera.jpg';image=Image.new('RGB',(80,40),'white')
   ImageDraw.Draw(image).rectangle((0,0,39,39),fill='red')
   exif=image.getexif();exif[274]=6;image.save(path,exif=exif,quality=100)
   region=rendering.render_region(path,1,[0,0,1,.5])
   self.assertEqual(region.size,(40,40));red,green,blue=region.getpixel((15,15))
   self.assertGreater(red,240);self.assertLess(green,15);self.assertLess(blue,15)
   for invalid in [[0,0,0,1],[-.1,0,.5,1],[0,0,float('nan'),1]]:
    with self.assertRaises(ValueError):rendering.render_region(path,1,invalid)
 def test_pdf_region_preserves_rotated_page_coordinates_and_source_bytes(self):
  import hashlib,pymupdf
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'rotated.pdf'
   with pymupdf.open() as document:
    page=document.new_page(width=80,height=40)
    page.draw_rect(pymupdf.Rect(0,0,40,40),color=None,fill=(1,0,0))
    page.set_rotation(90);document.save(path)
   before=hashlib.sha256(path.read_bytes()).hexdigest()
   image=rendering.render_region(path,1,[0,0,1,.5],400)
   self.assertEqual(image.size,(400,400));self.assertEqual(image.getpixel((150,150)),(255,0,0))
   self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
 def test_pdf_detail_renders_at_crop_resolution_instead_of_full_page_resolution(self):
  import pymupdf
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'small-dimensions.pdf'
   with pymupdf.open() as document:
    page=document.new_page(width=3000,height=2000)
    page.insert_text((1500,900),'WIDTH 6200',fontsize=6);document.save(path)
   image=rendering.image_inputs(path,[1],[.49,.44,.54,.49])[0]['image']
   self.assertEqual(max(image.size),2000)
   self.assertGreater(sum(1 for pixel in image.convert('L').getdata() if pixel<128),300)

if __name__=='__main__':unittest.main()
