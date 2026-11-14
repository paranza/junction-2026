"""Provider switching must preserve explicit settings and isolate credentials."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from server.config import load_environment

OPS = Path(__file__).resolve().parents[1] / 'ops'
sys.path.insert(0, str(OPS))
from deploy_verda import runtime_environment
from check_connections import load_runtime_config


class ProviderConfiguration(unittest.TestCase):
    def test_empty_gemini_preparation_does_not_switch_openai(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            root = Path(folder)
            (root / 'secrets.env').write_text('OPENAI_API_KEY=test-openai\n')
            (root / 'gemini.env').write_text('GEMINI_API_KEY=\nSTOA_PROVIDER=gemini\nSTOA_MODEL=gemini-4-carbon\n')
            (root / '.env').write_text('STOA_MODEL=existing-model\n')
            load_environment(root, private_env=root / 'secrets.env', gemini_env=root / 'gemini.env')
            self.assertNotIn('STOA_PROVIDER', os.environ)
            self.assertEqual(os.environ['STOA_MODEL'], 'existing-model')

    def test_key_activates_gemini_and_exports_override_private_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'STOA_MAX_MODEL_CALLS': '0'}, clear=True):
            root = Path(folder)
            gemini = root / 'gemini.env'
            gemini.write_text('GEMINI_API_KEY=test-gemini\nSTOA_PROVIDER=gemini\nSTOA_MODEL=gemini-4-carbon\nSTOA_MAX_MODEL_CALLS=50\n')
            load_environment(root, private_env=None, gemini_env=gemini)
            self.assertEqual(os.environ['STOA_PROVIDER'], 'gemini')
            self.assertEqual(os.environ['STOA_MAX_MODEL_CALLS'], '0')
            with patch.dict(os.environ, {'STOA_PROVIDER': 'openai', 'STOA_MODEL': 'test-openai-model'}, clear=True):
                load_environment(root, private_env=None, gemini_env=gemini)
                self.assertEqual(os.environ['STOA_MODEL'], 'test-openai-model')
                self.assertNotIn('GEMINI_API_KEY', os.environ)

    def test_deployment_matches_sidecar_selection_and_preserves_attempt_limit(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            root = Path(folder)
            secrets = root / 'secrets.env'
            secrets.write_text('OPENAI_API_KEY=test-openai\nVERDA_CLIENT_SECRET=test-cloud\n')
            gemini = root / 'gemini.env'
            gemini.write_text('GEMINI_API_KEY=test-gemini\nSTOA_PROVIDER=gemini\nSTOA_MODEL=gemini-4-carbon\nSTOA_MAX_MODEL_CALLS=57\n')
            config = load_runtime_config(secrets, gemini)
            env = runtime_environment(config).decode()
            self.assertIn('STOA_PROVIDER=gemini\n', env)
            self.assertIn('STOA_MAX_MODEL_CALLS=57\n', env)
            self.assertIn('GEMINI_API_KEY=test-gemini\n', env)
            self.assertNotIn('OPENAI_API_KEY', env)
            self.assertNotIn('VERDA_CLIENT_SECRET', env)

    def test_deployment_rejects_invalid_provider_key_or_multiline_setting(self):
        for config in ({'STOA_PROVIDER': 'other'}, {'STOA_PROVIDER': 'gemini'},
                       {'OPENAI_API_KEY': 'test\ninjected=value'},
                       {'GEMINI_API_KEY': 'test', 'STOA_PROVIDER': 'gemini', 'STOA_MODEL': 'bad\nmodel'},
                       {'OPENAI_API_KEY': 'test', 'STOA_MAX_MODEL_CALLS': '-1'}):
            with self.subTest(config_fields=list(config)):
                with self.assertRaises(ValueError):
                    runtime_environment(config)

    def test_bare_sidecar_key_chooses_gemini_default_model_in_both_loaders(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            root = Path(folder)
            secrets = root / 'secrets.env'
            secrets.write_text('OPENAI_API_KEY=test-openai\nSTOA_MODEL=old-openai-model\n')
            gemini = root / 'gemini.env'
            gemini.write_text('GEMINI_API_KEY=test-gemini\n')
            config = load_runtime_config(secrets, gemini)
            load_environment(root, private_env=secrets, gemini_env=gemini)
            for actual in (config, os.environ):
                self.assertEqual(actual['STOA_PROVIDER'], 'gemini')
                self.assertEqual(actual['STOA_MODEL'], 'gemini-4-carbon')

    def test_exported_google_key_does_not_activate_an_empty_sidecar(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'GOOGLE_API_KEY': 'unrelated-test-key'}, clear=True):
            root = Path(folder)
            secrets = root / 'secrets.env'
            secrets.write_text('OPENAI_API_KEY=test-openai\n')
            gemini = root / 'gemini.env'
            gemini.write_text('GEMINI_API_KEY=\nSTOA_PROVIDER=gemini\n')
            config = load_runtime_config(secrets, gemini)
            load_environment(root, private_env=secrets, gemini_env=gemini)
            self.assertNotIn('STOA_PROVIDER', config)
            self.assertNotIn('STOA_PROVIDER', os.environ)


if __name__ == '__main__':
    unittest.main()
