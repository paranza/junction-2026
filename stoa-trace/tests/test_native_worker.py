"""Real concurrent document parsing must not share native library handles."""
import concurrent.futures,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf
from server import extraction,native_worker,rendering
class NativeWorkerTests(unittest.TestCase):
 def test_concurrent_pdf_extraction_and_preview(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);paths=[]
   for index in range(4):
    path=root/f'plan-{index}.pdf'
    with pymupdf.open() as doc:
     page=doc.new_page(width=240,height=160);page.insert_text((20,40),f'Room {index}: 12.5 m2');doc.save(path)
    paths.append(path)
   def read(path):
    doc=extraction.extract_document(path,root)
    image,source=rendering.render_page(path,1,480)
    return doc['pages'][0]['text'],image.size,source
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(read,paths))
   for index,(text,size,source) in enumerate(results):
    self.assertIn(f'Room {index}: 12.5 m2',text);self.assertEqual(size,(480,320));self.assertEqual(source.resolve(),paths[index].resolve())
 def test_concurrent_ifc_geometry_queries(self):
  from tests.test_native_quality import IfcSourceGeometryQuality
  from server.native_qa import answer_native
  fixture=IfcSourceGeometryQuality()
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);paths=[]
   for index in range(4):
    model,context=fixture.model();fixture.room(model,context)
    path=root/f'geometry-{index}.ifc';model.write(path);paths.append(path)
   def read(path):
    document=extraction.extract_document(path,root)
    return answer_native('What is the net floor area of room Office in m²?',document,path,root)
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    answers=list(pool.map(read,paths))
   self.assertEqual([a['value'] for a in answers],[12.0]*4)
 def test_native_process_crash_is_a_file_error(self):
  with patch.object(native_worker.subprocess,'run',return_value=subprocess.CompletedProcess([], -11,stdout=b'')):
   with self.assertRaisesRegex(ValueError,'could not read'):
    native_worker.call('extract',path='/source.pdf',data_root='/')
 def test_parser_receives_no_model_credentials(self):
  with patch.dict(native_worker.os.environ,{'GEMINI_API_KEY':'private','CLOUDINARY_URL':'private'}),patch.object(native_worker.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout=b'{"ok":true,"result":{}}')) as run:
   native_worker.call('extract',path='/source.pdf',data_root='/')
   env=run.call_args.kwargs['env'];self.assertNotIn('GEMINI_API_KEY',env);self.assertNotIn('CLOUDINARY_URL',env)
if __name__=='__main__':unittest.main()
