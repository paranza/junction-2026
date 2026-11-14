"""Evidence and scope invariants with deterministic model fixtures; no API calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from server import llm


class EvidenceRules(unittest.TestCase):
    def setUp(self):
        self.document = {'page_count': 2, 'pages': [{'page': 1, 'text': 'A', 'words': []}, {'page': 2, 'text': 'B', 'words': []}],
                         'objects': [{'id': 'a', 'page': 1, 'bbox': [0.1, 0.1, 0.2, 0.2]}, {'id': 'b', 'page': 2, 'bbox': [0.8, 0.8, 0.9, 0.9]}],
                         'metadata': {'class_counts': {'IfcDoor': 200}}}
        self.inputs = [{'page': 1, 'region': [0, 0, 1, 1], 'kind': 'overview', 'image': Image.new('RGB', (100, 100), 'white')}]

    def result(self, **kwargs):
        return {'answer': 'The model claims 999 doors', 'operation': 'count', 'value': 999, 'unit': 'count',
                'scope': 'Page 1', 'complete': True, 'needs_review': False, 'warnings': [], 'calculation': None,
                'evidence': [], **kwargs}

    def run_model(self, result, **kwargs):
        with patch.object(llm, '_request', return_value=result), patch.object(llm, 'image_inputs', return_value=self.inputs):
            return llm.answer_with_model('How many doors?', self.document, Path('drawing.pdf'), scope='page', **kwargs)

    def test_count_uses_distinct_citations_and_discards_out_of_scope_ids(self):
        item = lambda oid: {'object_id': oid, 'image_index': None, 'bbox': None, 'label': 'Door', 'quoted_text': '', 'value': None, 'unit': None}
        answer = self.run_model(self.result(evidence=[item('a'), item('a'), item('b')]))
        self.assertEqual(answer['value'], 1)
        self.assertEqual(len(answer['evidence']), 1)
        self.assertNotIn('999', answer['answer'])

    def test_no_citation_removes_unsupported_numeric_claim(self):
        answer = self.run_model(self.result())
        self.assertIsNone(answer['value'])
        self.assertEqual(answer['status'], 'insufficient_evidence')
        self.assertNotIn('999', answer['answer'])

    def test_page_and_region_context_exclude_global_totals(self):
        context = llm._scoped_context(self.document, Path('drawing.pdf'), 1, 'page', [0, 0, 0.5, 0.5], [1])
        self.assertEqual([o['id'] for o in context['objects']], ['a'])
        self.assertNotIn('class_counts', context['metadata'])
        self.assertEqual([p['page'] for p in context['pages']], [1])

    def test_invalid_and_duplicate_image_boxes_are_discarded(self):
        def item(box):
            return {'object_id': None, 'image_index': 0, 'bbox': box, 'label': 'Door', 'quoted_text': '', 'value': None, 'unit': None}
        answer = self.run_model(self.result(evidence=[item([0.1, 0.1, 0.2, 0.2]), item([0.1, 0.1, 0.2, 0.2]), item([0.8, 0.8, 0.2, 0.2])]))
        self.assertEqual(answer['value'], 1)

    def test_unsupported_measurement_cannot_retain_numeric_claim(self):
        item = {'object_id': 'a', 'image_index': None, 'bbox': None, 'label': 'Room', 'quoted_text': '', 'value': None, 'unit': None}
        answer = self.run_model(self.result(operation='area', value=999, unit='m²', evidence=[item]))
        self.assertIsNone(answer['value'])
        self.assertNotIn('999', answer['answer'])

    def test_total_area_requires_every_page(self):
        document = {**self.document, 'page_count': 10, 'pages': [{'page': i, 'text': 'Area'} for i in range(1, 11)]}
        result = self.result(operation='area', unit='m²', evidence=[{'object_id': 'a', 'image_index': None, 'bbox': None,
                             'label': 'Room A', 'quoted_text': '30 m²', 'value': 30, 'unit': 'm²'}])
        with patch.object(llm, '_request', return_value=result), patch.object(llm, 'image_inputs', return_value=self.inputs):
            answer = llm.answer_with_model('What is the total area of all rooms?', document, Path('drawing.pdf'))
        self.assertIsNone(answer['value'])
        self.assertEqual(answer['status'], 'insufficient_evidence')

    def test_ifc_second_view_preserves_linked_pdf_page_one(self):
        with tempfile.TemporaryDirectory() as folder:
            views = [Path(folder) / 'floor1.pdf', Path(folder) / 'floor2.pdf']
            for view in views:
                view.touch()
            linked = {'objects': [{'id': 'x', 'page': 1, 'source_path': str(views[1])}], 'pages': [{'page': 1, 'text': 'Floor 2'}]}
            with patch('server.rendering.visual_sources', return_value=views), patch('server.extraction.extract_cached', return_value=linked):
                context = llm._scoped_context(self.document, Path('model.ifc'), 2, 'page', None, [2])
            self.assertEqual(context['objects'][0]['page'], 1)
            self.assertEqual(context['objects'][0]['source_path'], str(views[1]))

    def test_visual_source_unit_aliases_and_conversions_are_reproduced(self):
        item={'object_id':None,'image_index':0,'bbox':[.1,.1,.2,.2],
              'label':'Printed floor area','quoted_text':'100 SF','value':100,'unit':'SF'}
        result=self.result(operation='area',value=999,unit='m²',evidence=[item])
        with patch.object(llm,'_request',return_value=result),patch.object(llm,'image_inputs',return_value=self.inputs):
            answer=llm.answer_with_model('What is the printed floor area in square metres?',self.document,Path('scan.png'),scope='page')
        self.assertAlmostEqual(answer['value'],9.290304)
        self.assertEqual(answer['evidence'][0]['value'],100)
        self.assertIn('100 SF',answer['calculation']);self.assertEqual(answer['status'],'needs_review')

    def test_a_length_cannot_be_accepted_as_an_area_from_a_raster(self):
        item={'object_id':None,'image_index':0,'bbox':[.1,.1,.2,.2],
              'label':'Dimension','quoted_text':'100 mm','value':100,'unit':'mm'}
        for target in ['m²','mm']:
            result=self.result(operation='area',value=999,unit=target,evidence=[item])
            with patch.object(llm,'_request',return_value=result),patch.object(llm,'image_inputs',return_value=self.inputs):
                answer=llm.answer_with_model('What is the area?',self.document,Path('scan.png'),scope='page')
            self.assertIsNone(answer['value'])


if __name__ == '__main__':
    unittest.main()
