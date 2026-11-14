import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('generalization_corpus',Path(__file__).resolve().parents[1]/'ops/generalization_corpus.py')
corpus=importlib.util.module_from_spec(spec);spec.loader.exec_module(corpus)


class IndependentCorpus(unittest.TestCase):
    def test_source_variation_has_no_hidden_answer_attributes(self):
        first,a=corpus.schematic(100,'printed_area');second,b=corpus.schematic(101,'unscaled_area')
        self.assertNotEqual(first,second)
        self.assertNotIn('data-expected',first)
        self.assertNotIn('id="door',first)
        self.assertIsNone(b['area'])
        self.assertEqual(len(a['door_boxes']),a['doors'])
        for box in a['door_boxes']+b['door_boxes']:
            self.assertTrue(all(0<=x<=1 for x in box))

    def test_six_formats_frozen_once_and_labels_separated_from_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            freeze=corpus.generate(root)
            self.assertEqual({x['format'] for x in freeze['inputs']},set(corpus.FORMATS))
            self.assertEqual(freeze['splits']['development']['groups'],6)
            dev=corpus.load_lines(root/'development-requests.jsonl')
            reserve=corpus.load_lines(root/'reserved-requests.jsonl')
            self.assertTrue({x['path'] for x in dev}.isdisjoint(x['path'] for x in reserve))
            self.assertTrue(all('expected_value' not in row and 'expected_boxes' not in row for row in dev+reserve))
            with self.assertRaises(ValueError):corpus.generate(root)

    def case(self,expected,task='doors',unit='count'):
        return {'case_id':'one','path':'inputs/a.png','question':'Question?', 'task':task,'kind':'procedural',
                'expected_value':expected,'unit':unit,'scoreable':True}

    def answer(self,value,status='visual',unit='count',**extra):
        return {'path':'inputs/a.png','question':'Question?','value':value,'status':status,'unit':unit,'answer':'Source result',**extra}

    def test_exact_counts_and_area_unit_conversion(self):
        gold={'split':'development','cases':[self.case(4)]}
        self.assertEqual(corpus.score(gold,[self.answer(4)],'abcdef1')['numeric_correct'],1)
        self.assertEqual(corpus.score(gold,[self.answer(4.1)],'abcdef1')['numeric_correct'],0)
        gold['cases']=[self.case(10,'area','m²')]
        self.assertEqual(corpus.score(gold,[self.answer(10/.09290304,unit='ft²')],'abcdef1')['numeric_correct'],1)
        self.assertEqual(corpus.score(gold,[self.answer(10,unit='m')],'abcdef1')['numeric_correct'],0)

    def test_required_abstention_is_separate_and_errors_do_not_pass(self):
        gold={'split':'reserved','cases':[self.case(None,'area','m²')]}
        score=corpus.score(gold,[self.answer(None,'insufficient_evidence',unit=None)],'abcdef1')
        self.assertEqual(score['numeric_cases'],0)
        self.assertEqual(score['correct_required_abstentions'],1)
        self.assertEqual(corpus.score(gold,[self.answer(None,'error')],'abcdef1')['correct_required_abstentions'],0)
        bad=self.answer(None);bad.pop('answer')
        self.assertEqual(corpus.score(gold,[bad],'abcdef1')['correct_required_abstentions'],0)

    def test_evidence_requires_one_to_one_spatial_match(self):
        case=self.case(2);case['expected_boxes']=[[0,.1,.1,.2],[.4,.4,.5,.5]]
        answer=self.answer(2,evidence=[{'bbox':[0,.1,.1,.2]},{'bbox':[0,.1,.1,.2]}])
        score=corpus.score({'split':'development','cases':[case]},[answer],'abcdef1')
        self.assertEqual(score['object_precision'],.5)
        self.assertEqual(score['object_recall'],.5)

    def test_unknown_duplicate_and_unrun_rows_are_explicit(self):
        gold={'split':'development','cases':[self.case(4)]}
        self.assertEqual(corpus.score(gold,[],'abcdef1')['unrun_cases'],1)
        with self.assertRaises(ValueError):corpus.score(gold,[self.answer(4),self.answer(4)],'abcdef1')
        with self.assertRaises(ValueError):corpus.score(gold,[{**self.answer(4),'path':'other.png'}],'abcdef1')


if __name__=='__main__':unittest.main()
