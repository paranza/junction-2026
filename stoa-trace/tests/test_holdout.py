import copy
from contextlib import redirect_stderr
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

OPS = Path(__file__).resolve().parents[1] / 'ops'
sys.path.insert(0, str(OPS))
spec = importlib.util.spec_from_file_location('freeze_holdout', OPS / 'freeze_holdout.py')
holdout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(holdout)


def cases():
    result = []
    for building in range(1, 11):
        for floor in (1, 2):
            for language in ('en', 'fi'):
                path = f'data/swiss_dwellings/site1_bldg{building}_floor{floor}.pdf'
                source, group = holdout.drawing_group(path)
                result.append({'id': f'{building}/{floor}/{language}', 'path': path,
                               'question': language + ' question', 'expected': building,
                               'source': source, 'group': group})
    return result


class ProspectiveReservation(unittest.TestCase):
    def test_related_floors_and_translations_never_cross_split(self):
        dev, reserved, groups, excluded, allocation = holdout.split_groups(cases(), .2, 'fixed-seed')
        self.assertEqual(len(groups), 10)
        self.assertEqual(len({case['group'] for case in reserved}), 2)
        self.assertFalse({case['group'] for case in dev} & {case['group'] for case in reserved})
        self.assertEqual(len(dev) + len(reserved), len(cases()))

    def test_selection_is_seeded_order_independent_and_never_uses_labels(self):
        original = cases()
        changed = list(reversed(copy.deepcopy(original)))
        for case in changed:
            case['expected'] = 'entirely different label'
        first = holdout.split_groups(original, .2, 'fixed-seed')[1]
        again = holdout.split_groups(changed, .2, 'fixed-seed')[1]
        self.assertEqual({c['group'] for c in first}, {c['group'] for c in again})
        self.assertEqual(original, cases())

    def test_known_demo_groups_are_always_development(self):
        excluded = {'swiss_dwellings:site1_bldg1', 'swiss_dwellings:site1_bldg2'}
        dev, reserved, groups, kept, allocation = holdout.split_groups(cases(), .2, 'fixed-seed', excluded)
        self.assertTrue(excluded <= {c['group'] for c in dev})
        self.assertFalse(excluded & {c['group'] for c in reserved})
        self.assertEqual(kept, excluded)

    def test_public_record_has_no_question_or_answer_fields(self):
        full = cases()
        dev, reserved, groups, excluded, allocation = holdout.split_groups(full, .2, 'seed')
        original = {'cases': full, 'cases_sha256': holdout.canonical_hash(full),
                    'dataset': {'questions_sha256': 'a' * 64}}
        record = holdout.make_record(original, dev, reserved, groups, excluded, allocation,
                                     seed='seed', fraction=.2, frozen_at='now', commit='commit')
        encoded = json.dumps(record)
        self.assertNotIn('"expected"', encoded)
        self.assertNotIn('"question"', encoded)
        self.assertIn('not an untouched test set', record['exposure_note'])

    def test_restored_membership_reproduces_split_and_refuses_changed_input(self):
        full = cases()
        dev, reserved, groups, excluded, allocation = holdout.split_groups(full, .2, 'seed')
        original = {'cases': full, 'cases_sha256': holdout.canonical_hash(full),
                    'dataset': {'questions_sha256': 'a' * 64}}
        record = holdout.make_record(original, dev, reserved, groups, excluded, allocation,
                                     seed='seed', fraction=.2, frozen_at='now', commit='commit')
        restored_dev, restored_hold, restored_groups = holdout.restore_split(original, record)
        self.assertEqual(restored_dev, dev)
        self.assertEqual(restored_hold, reserved)
        changed = copy.deepcopy(original)
        changed['cases_sha256'] = 'changed'
        with self.assertRaises(ValueError):
            holdout.restore_split(changed, record)
        changed_record = copy.deepcopy(record)
        changed_record['reserved_group_membership'].pop()
        with self.assertRaises(ValueError):
            holdout.restore_split(original, changed_record)

    def test_frozen_outputs_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'development.json'
            output.write_text('preserve me')
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    holdout.main(['--manifest', str(root / 'missing.json'), '--output-dir', str(root),
                                  '--membership-output', str(root / 'membership.json')])
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(output.read_text(), 'preserve me')

    def test_invalid_or_infeasible_reservation_is_rejected(self):
        with self.assertRaises(ValueError):
            holdout.split_groups(cases(), 1, 'seed')
        with self.assertRaises(ValueError):
            holdout.split_groups(cases(), .2, 'seed', {c['group'] for c in cases()})


if __name__ == '__main__':
    unittest.main()
