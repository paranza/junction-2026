"""Independent format fixtures; no model API or benchmark labels."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

from server import rendering, store
from server.app import app
from server.extraction import extract_document


class GeneralRasterFormats(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, suffix, mode='RGB', color='white'):
        path = self.root / ('independent-plan' + suffix)
        Image.new(mode, (40, 30), color).save(path)
        return path

    def test_common_web_formats_have_real_metadata_and_rgb_previews(self):
        for suffix in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff'):
            with self.subTest(suffix=suffix):
                path = self.fixture(suffix)
                document = extract_document(path, self.root)
                self.assertEqual(document['page_count'], 1)
                self.assertEqual(document['pages'][0]['width'], 40)
                self.assertEqual(document['objects'], [])
                image, actual_source = rendering.render_page(path)
                self.assertEqual(actual_source, path)
                self.assertEqual(image.mode, 'RGB')
                self.assertEqual(image.size, (40, 30))
                self.assertIn(suffix, store.FORMATS)

    def test_transparent_raster_is_composited_on_white(self):
        path = self.fixture('.png', mode='RGBA', color=(0, 0, 0, 0))
        image, _ = rendering.render_page(path)
        self.assertEqual(image.getpixel((10, 10)), (255, 255, 255))

    def test_tiff_pages_are_not_flattened_or_repeated(self):
        path = self.root / 'separate-scanned-sheets.tiff'
        first = Image.new('RGB', (31, 19), 'red')
        second = Image.new('RGB', (20, 40), 'blue')
        first.save(path, save_all=True, append_images=[second])
        document = extract_document(path, self.root)
        self.assertEqual(document['page_count'], 2)
        self.assertEqual([(p['width'], p['height']) for p in document['pages']], [(31, 19), (20, 40)])
        image, _ = rendering.render_page(path, page=2)
        self.assertEqual(image.size, (20, 40))
        self.assertEqual(image.getpixel((10, 10)), (0, 0, 255))
        inputs = rendering.image_inputs(path, [2])
        self.assertEqual(inputs[0]['page'], 2)
        self.assertEqual(inputs[0]['image'].getpixel((10, 10)), (0, 0, 255))
        with self.assertRaises(ValueError):
            rendering.render_page(path, page=3)

    def test_gif_animation_uses_only_first_frame_and_warns(self):
        path = self.root / 'animated-plan.gif'
        Image.new('RGB', (40, 30), 'red').save(path, save_all=True,
            append_images=[Image.new('RGB', (40, 30), 'blue')], duration=100, loop=0)
        document = extract_document(path, self.root)
        self.assertEqual(document['page_count'], 1)
        self.assertTrue(any('first frame' in warning for warning in document['warnings']))
        image, _ = rendering.render_page(path)
        self.assertEqual(image.getpixel((10, 10)), (255, 0, 0))
        with self.assertRaises(ValueError):
            rendering.render_page(path, page=2)

    def test_exif_orientation_matches_page_metadata(self):
        for suffix in ('.jpg', '.tiff'):
            with self.subTest(suffix=suffix):
                path = self.root / ('rotated-camera-plan' + suffix)
                image = Image.new('RGB', (40, 30), 'white')
                exif = image.getexif()
                exif[274] = 6
                image.save(path, exif=exif)
                document = extract_document(path, self.root)
                preview, _ = rendering.render_page(path)
                self.assertEqual(preview.size, (30, 40))
                self.assertEqual((document['pages'][0]['width'], document['pages'][0]['height']), preview.size)

    def test_decoded_tiff_content_keeps_pages_despite_a_misleading_extension(self):
        path = self.root / 'downloaded-as.png'
        Image.new('RGB', (20, 20), 'red').save(path, format='TIFF', save_all=True,
            append_images=[Image.new('RGB', (20, 20), 'blue')])
        document = extract_document(path, self.root)
        self.assertEqual(document['page_count'], 2)
        image, _ = rendering.render_page(path, page=2)
        self.assertEqual(image.getpixel((10, 10)), (0, 0, 255))

    def test_corrupt_supported_image_is_rejected_instead_of_becoming_an_empty_plan(self):
        path = self.root / 'broken.webp'
        path.write_bytes(b'not a drawing')
        with self.assertRaises(OSError):
            extract_document(path, self.root)
        with self.assertRaises(OSError):
            rendering.render_page(path)

    def test_disguised_postscript_does_not_reach_an_external_decoder(self):
        path = self.root / 'actually-postscript.png'
        Image.new('RGB', (20, 20)).save(path, format='EPS')
        with patch.object(rendering.ImageOps, 'exif_transpose', side_effect=AssertionError('Must reject before image decoding')):
            with self.assertRaisesRegex(ValueError, 'Unsupported image encoding'):
                rendering.render_page(path)
        with self.assertRaisesRegex(ValueError, 'Unsupported image encoding'):
            extract_document(path, self.root)

    def test_file_pixel_and_tiff_page_limits_are_enforced(self):
        path = self.fixture('.png')
        for name, limit in [('MAX_RASTER_BYTES', 1), ('MAX_RASTER_PIXELS', 20)]:
            with self.subTest(limit=name), patch.object(rendering, name, limit):
                with self.assertRaises(ValueError):
                    extract_document(path, self.root)
                with self.assertRaises(ValueError):
                    rendering.render_page(path)
        tiff = self.root / 'two.tiff'
        Image.new('RGB', (10, 10)).save(tiff, save_all=True,
            append_images=[Image.new('RGB', (10, 10))])
        with patch.object(rendering, 'MAX_RASTER_PAGES', 1):
            with self.assertRaises(ValueError):
                extract_document(tiff, self.root)

    def test_unsupported_dwg_remains_an_explicit_conversion_requirement(self):
        path = self.root / 'unknown.dwg'
        path.write_bytes(b'not a supported native drawing')
        document = extract_document(path, self.root)
        self.assertEqual(document['objects'], [])
        self.assertTrue(any('conversion' in message for message in document['warnings']))
        with self.assertRaises(ValueError):
            rendering.render_page(path)

    def test_api_accepts_tiff_and_renders_the_requested_scanned_page(self):
        path = self.root / 'new-upload.tiff'
        Image.new('RGB', (30, 20), 'red').save(path, save_all=True,
            append_images=[Image.new('RGB', (30, 20), 'blue')])
        runtime = self.root / 'runtime'
        for name in ('uploads', 'cache', 'previews'):
            (runtime / name).mkdir(parents=True, exist_ok=True)
        with patch.multiple(store, RUNTIME=runtime, DATA_ROOT=self.root / 'no-dataset'), TestClient(app) as client:
            response = client.post('/api/upload', files=[('files', ('new-upload.tiff', path.read_bytes(), 'image/tiff'))])
            self.assertEqual(response.status_code, 200, response.text)
            doc_id = response.json()['documents'][0]['id']
            detail = client.get('/api/documents/' + doc_id)
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()['page_count'], 2)
            preview = client.get(f'/api/documents/{doc_id}/pages/2/image')
            self.assertEqual(preview.status_code, 200, preview.text[:100])
            image = Image.open(io.BytesIO(preview.content))
            self.assertEqual(image.getpixel((10, 10)), (0, 0, 255))
            self.assertEqual(client.get(f'/api/documents/{doc_id}/pages/3/image').status_code, 422)
            with patch('server.llm._request', side_effect=AssertionError('Native-only mode must not call a model')):
                answer = client.post('/api/ask', json={'document_id': doc_id, 'question': 'How many doors?',
                                                       'mode': 'native', 'scope': 'page', 'page': 2})
            self.assertEqual(answer.status_code, 200)
            self.assertIsNone(answer.json()['value'])


if __name__ == '__main__':
    unittest.main()
