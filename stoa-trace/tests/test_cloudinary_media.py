"""Protected evidence derivatives: provider calls are mocked and label-free."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from PIL import Image

from server import app as api, cloudinary_media as media, store


def picture(width=240, height=120):
    stream = io.BytesIO()
    Image.new('RGB', (width, height), 'white').save(stream, format='PNG')
    return stream.getvalue()


class ProtectedCloseups(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        runtime = root / 'runtime'
        for part in ('', 'cache', 'previews', 'uploads'):
            (runtime / part).mkdir(parents=True, exist_ok=True)
        self.patches = [patch.object(store, 'RUNTIME', runtime), patch.object(store, 'DATA_ROOT', root / 'dataset'),
                        patch.dict(os.environ, {'CLOUDINARY_URL': 'cloudinary://mock-key:mock-secret@mock-cloud'})]
        for item in self.patches:
            item.start()
        self.client = TestClient(api.app).__enter__()
        self.doc = self.client.post('/api/upload', files={'files': ('drawing.png', picture(), 'image/png')}).json()['documents'][0]
        self.answer = {'id': 'answer-one', 'document_id': self.doc['id'], 'question': 'Count doors',
                       'value': 1, 'unit': 'count', 'evidence': [{'id': 'door/1', 'page': 1, 'bbox': [.1, .2, .3, .5]}],
                       'provenance': {'source_fingerprint': store.source_fingerprint(self.doc['id'])}}
        store.save_answer(self.answer['id'], self.doc['id'], self.answer['question'], self.answer)
        self.uploader, self.utils = Mock(), Mock()
        self.uploader.upload.side_effect = lambda file, **kw: {
            'public_id': kw['public_id'], 'version': 123, 'width': 240, 'height': 120, 'type': 'authenticated'}
        self.utils.cloudinary_url.return_value = ('https://res.cloudinary.com/mock-cloud/image/authenticated/s--mock--/asset.png', {})

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def post(self, answer_id='answer-one', evidence_id='door%2F1'):
        return self.client.post('/api/answers/' + answer_id + '/evidence/' + evidence_id + '/closeup')

    def mocks(self):
        return patch.object(media, '_sdk', return_value=(self.uploader, self.utils)), patch.object(media, '_download', return_value=(picture(192, 168), (192, 168)))

    def test_upload_once_authenticated_crop_cache_and_protected_delivery(self):
        sdk, download = self.mocks()
        with sdk, download:
            first = self.post()
            self.assertEqual(first.status_code, 200, first.text)
            body = first.json()
            self.assertRegex(body['image_url'], r'^/api/media/[a-f0-9]{64}\.png$')
            self.assertFalse(body['cache_hit'])
            self.assertNotIn('mock-secret', first.text)
            self.assertNotIn('res.cloudinary.com', first.text)
            self.assertEqual(self.client.get(body['image_url']).content, picture(192, 168))
            self.assertTrue(self.post().json()['cache_hit'])
            second_answer = {**self.answer, 'id': 'answer-two'}
            store.save_answer('answer-two', self.doc['id'], 'Repeat', second_answer)
            self.assertEqual(self.post('answer-two').status_code, 200)
        self.assertEqual(self.uploader.upload.call_count, 1)
        self.assertEqual(self.uploader.explicit.call_count, 2)
        options = self.uploader.upload.call_args.kwargs
        self.assertEqual(options['type'], 'authenticated')
        self.assertEqual(options['resource_type'], 'image')
        self.assertFalse(options['overwrite'])
        self.assertEqual(options['upload_preset'], media.PRESET)
        self.assertEqual(self.uploader.explicit.call_args.kwargs['type'], 'authenticated')
        crop = self.uploader.explicit.call_args.kwargs['eager'][0]['transformation'][0]
        self.assertEqual(crop, {'crop': 'crop', 'gravity': 'north_west', 'x': 14, 'y': 16, 'width': 68, 'height': 52})
        with store.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE kind='model_request'").fetchone()[0], 0)

    def test_changed_source_revokes_new_and_cached_closeups(self):
        sdk, download = self.mocks()
        with sdk, download:
            first = self.post().json()
            store.get_path(self.doc['id']).write_bytes(picture(241, 121))
            self.assertEqual(self.post().status_code, 409)
            self.assertEqual(self.client.get(first['image_url']).status_code, 409)
        self.assertEqual(self.uploader.upload.call_count, 1)

    def test_missing_locations_invalid_pages_and_unknown_ids_never_upload(self):
        for item in ({'id': 'bad'}, {'id': 'bad', 'bbox': [0, 0, 1, float('nan')]},
                     {'id': 'bad', 'bbox': [0, 0, 1, 1], 'page': 2}):
            with self.subTest(item=item):
                store.update_answer(self.answer['id'], {**self.answer, 'evidence': [item]})
                sdk, download = self.mocks()
                with sdk, download:
                    self.assertEqual(self.post(evidence_id='bad').status_code, 422)
        self.assertEqual(self.post(evidence_id='missing').status_code, 404)
        self.uploader.upload.assert_not_called()

    def test_saved_polygon_excluded_object_and_linked_document_are_supported(self):
        linked = self.client.post('/api/upload', files={'files': ('linked.png', picture(240, 120), 'image/png')}).json()['documents'][0]
        item = {'id': 'linked', 'page': 1, 'document_id': linked['id'], 'excluded': True,
                'polygon': [[.1, .2], [.3, .2], [.3, .5], [.1, .5]]}
        store.update_answer(self.answer['id'], {**self.answer, 'evidence': [item]})
        sdk, download = self.mocks()
        with sdk, download, patch.object(media, '_source', wraps=media._source) as source:
            result = self.post(evidence_id='linked')
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(source.call_args.args, (self.answer['id'], 'linked'))
        self.assertEqual(self.uploader.upload.call_count, 1)

    def test_no_configuration_and_provider_failure_are_sanitized(self):
        with patch.dict(os.environ, {'CLOUDINARY_URL': ''}):
            self.assertFalse(self.client.get('/api/media/status').json()['available'])
            self.assertEqual(self.post().status_code, 503)
        sdk, download = self.mocks()
        self.uploader.upload.side_effect = RuntimeError('mock-secret http://private-provider-url')
        with sdk, download:
            result = self.post()
            self.assertEqual(result.status_code, 503)
            self.assertNotIn('mock-secret', result.text)
            self.assertNotIn('private-provider', result.text)

    def test_proxy_rejects_arbitrary_remote_url_without_network(self):
        for url in ('https://evil.test/asset.png', 'http://res.cloudinary.com/mock-cloud/image/authenticated/s--x--/a.png',
                    'https://res.cloudinary.com/another-cloud/image/authenticated/s--x--/a.png'):
            with self.subTest(url=url), patch('httpx.Client') as network, self.assertRaises(media.MediaError):
                media._download(url, media.credentials())
            network.assert_not_called()
        self.assertEqual(self.client.get('/api/media/not-a-token.png').status_code, 404)


class ProviderTransport(unittest.TestCase):
    def test_sdk_transport_cannot_retry_or_redirect_mutations(self):
        actual = Mock()
        transport = media._NoReplayTransport(actual)
        transport.request('POST', 'https://api.cloudinary.com', retries=4, redirect=True)
        self.assertFalse(actual.request.call_args.kwargs['retries'])
        self.assertFalse(actual.request.call_args.kwargs['redirect'])


class MediaConfiguration(unittest.TestCase):
    def test_private_sidecar_exports_override_and_deployment_stdin_configuration(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ops'))
        from server.config import load_environment
        from check_connections import load_runtime_config
        from deploy_verda import runtime_environment
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            private = root / 'cloudinary.env'
            private.write_text('CLOUDINARY_URL=cloudinary://fake-key:fake-secret@fake-cloud\n')
            secrets = root / 'secrets.env'
            secrets.write_text('OPENAI_API_KEY=test-provider-key\nVERDA_CLIENT_SECRET=not-for-runtime\n')
            load_environment(root, private_env=None, gemini_env=None, cloudinary_env=private)
            self.assertEqual(media.credentials().cloud_name, 'fake-cloud')
            config = load_runtime_config(secrets, gemini_path=None, cloudinary_path=private)
            wire = runtime_environment(config).decode()
            self.assertIn('CLOUDINARY_URL=cloudinary://fake-key:fake-secret@fake-cloud\n', wire)
            self.assertNotIn('VERDA_CLIENT_SECRET', wire)
            with patch.dict(os.environ, {'CLOUDINARY_URL': 'cloudinary://other-key:other-secret@other-cloud'}):
                load_environment(root, private_env=None, gemini_env=None, cloudinary_env=private)
                self.assertEqual(media.credentials().cloud_name, 'other-cloud')
                override = load_runtime_config(secrets, gemini_path=None, cloudinary_path=private)
                self.assertEqual(override['CLOUDINARY_URL'], os.environ['CLOUDINARY_URL'])


if __name__ == '__main__':
    unittest.main()
