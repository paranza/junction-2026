"""Drawing groups and evaluation operands remain separate from inference."""
import importlib.util
from pathlib import Path
import sys
import unittest

OPS = Path(__file__).resolve().parents[1] / 'ops'
sys.path.insert(0, str(OPS))
from grouped_manifest import drawing_group, select_cases
from benchmark import aggregate


class EvaluationGroups(unittest.TestCase):
    def test_sibling_exports_and_translations_share_groups(self):
        paths = ['data/swiss_dwellings/site12_bldg34_floor56.pdf',
                 'data/swiss_dwellings/site12_bldg34_floor99.dxf']
        self.assertEqual(drawing_group(paths[0]), drawing_group(paths[1]))
        self.assertEqual(drawing_group('data/ifc_models/house.ifc'), drawing_group('data/ifc_models/house_plan-02-level.pdf'))
        self.assertEqual(drawing_group('data/opening_design/Project/A.pdf'), drawing_group('data/opening_design/Project/B.dwg'))

    def test_excluded_groups_never_selected_and_labels_do_not_select(self):
        rows = [{'path': f'data/cubicasa5k/plan{i}.png', 'question': 'How many doors?',
                 'answer': i, 'unit': 'count', 'type': 'count'} for i in range(12)]
        excluded = {'cubicasa5k:plan2', 'cubicasa5k:plan8'}
        a = select_cases(rows, excluded, 6, 'seed')
        b = select_cases([{**r, 'answer': 999} for r in rows], excluded, 6, 'seed')
        self.assertEqual([c['id'] for c in a], [c['id'] for c in b])
        self.assertFalse({c['group'] for c in a} & excluded)

    def test_maximum_per_building_survives_many_formats(self):
        rows = [{'path': f'data/swiss_dwellings/site1_bldg1_floor{i}.pdf', 'question': 'How many doors?',
                 'answer': i, 'unit': 'count', 'type': 'count'} for i in range(12)]
        self.assertEqual(len(select_cases(rows, set(), 10, 'seed', max_per_group=2)), 2)

    def test_empty_report_does_not_invent_known_cost(self):
        self.assertIsNone(aggregate([])['usage']['cost_estimate_usd'])


if __name__ == '__main__':
    unittest.main()
