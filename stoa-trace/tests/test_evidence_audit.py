"""Evidence scoring does not equate a valid box with a correct object."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ops'))
from evidence_audit import audit, match_evidence


class EvidenceAudit(unittest.TestCase):
    def test_duplicate_predictions_do_not_inflate_recall(self):
        gold = [{'page': 1, 'bbox': [.1, .1, .2, .2]}]
        predicted = [dict(gold[0]), dict(gold[0])]
        self.assertEqual(match_evidence(predicted, gold), {'true_positive': 1, 'false_positive': 1, 'false_negative': 0})

    def test_wrong_source_page_or_class_is_not_a_match(self):
        gold = [{'page': 2, 'category': 'window', 'bbox': [.1, .1, .2, .2]}]
        for prediction in ({**gold[0], 'page': 1}, {**gold[0], 'category': 'door'}):
            self.assertEqual(match_evidence([prediction], gold)['true_positive'], 0)

    def test_unreviewed_annotations_do_not_become_ground_truth(self):
        report = {'results': [{'id': 'a', 'response': {'evidence': []}}]}
        result = audit(report, {'cases': [{'case_id': 'a', 'reviewed': False, 'expected_objects': []}]})
        self.assertEqual(result['reviewed_cases'], 0)
        self.assertIsNone(result['answer_support_rate'])

    def test_reviewed_case_requires_actual_judgment(self):
        report = {'results': [{'id': 'a', 'response': {'evidence': []}}]}
        with self.assertRaises(ValueError):
            audit(report, {'cases': [{'case_id': 'a', 'reviewed': True, 'expected_objects': []}]})


if __name__ == '__main__':
    unittest.main()
