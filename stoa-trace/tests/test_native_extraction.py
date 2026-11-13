"""Native evidence and unsupported-filter regressions, without API calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server.extraction import extract_document
from server.native_qa import answer_native


class NativeQARegressionTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.gettempdir())
        self.model={"format":"ifc","metadata":{"storeys":[]},"objects":[
            {"id":"d1","guid":"g1","label":"Door 1","type":"IfcDoor","page":1,"properties":{}},
            {"id":"d2","guid":"g2","label":"Door 2","type":"IfcDoor","page":1,"properties":{}},
        ]}

    def test_model_counts_distinct_objects_and_retains_guids(self):
        result=answer_native("How many doors are there in the model?",self.model,self.root/'example.ifc',self.root)
        self.assertEqual(result['value'],2)
        self.assertEqual(len(result['evidence']),2)
        self.assertFalse(result['spatial_evidence_complete'])

    def test_unsupported_filters_never_return_unfiltered_count(self):
        for question in ("How many fire doors are there?", "How many blue doors are there?",
                         "How many doors wider than 1m?", "How many doors are on the second floor?",
                         "How many doors and windows are there?",'How many "blue" doors?',
                         'How many "fire" doors?', 'How many doors on floor "second"?',
                         'How many doors on "second" floor?'):
            with self.subTest(question=question):
                self.assertIsNone(answer_native(question,self.model,self.root/'example.ifc',self.root))

    def test_quoted_model_title_does_not_become_a_filter(self):
        for question in ('How many doors are there in the model "Blue Fire Building"?',
                         "How many doors are there in the building 'Blue Fire Building'?"):
            with self.subTest(question=question):
                result=answer_native(question,self.model,self.root/'example.ifc',self.root)
                self.assertEqual(result['value'],2)

    def test_quoted_known_storey_is_a_resolved_scope(self):
        self.model['metadata']['storeys']=[{'guid':'s1','name':'1.korrus'}]
        for obj in self.model['objects']:obj['properties']['storey_guid']='s1'
        result=answer_native("How many doors are on floor '1.korrus'?",self.model,self.root/'example.ifc',self.root)
        self.assertEqual(result['value'],2)

    def test_room_number_not_found_does_not_sum_same_named_rooms(self):
        document={"metadata":{},"objects":[{"id":"r1","type":"room","label":"Stanza","page":1,
                    "bbox":[.1,.1,.2,.2],"properties":{"room_number":"5.11","net_area_m2":13.62}}]}
        self.assertIsNone(answer_native("What is the area of room 5.99 ('Stanza') in m²?",document,self.root/'example.pdf',self.root))
        result=answer_native("What is the area of room 5.11 ('Stanza') in m²?",document,self.root/'example.pdf',self.root)
        self.assertEqual(result['value'],13.62)

    def test_svg_viewbox_origin_is_subtracted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/'plan.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 200 100 100">'
                            '<g class="IfcSpace" data-guid="abc" data-name="Office">'
                            '<path d="M100,200 L200,200 L200,300 L100,300 Z"/></g></svg>')
            result=extract_document(path,root)
            self.assertEqual(result['objects'][0]['bbox'],[0,0,1,1])
            self.assertEqual(result['objects'][0]['guid'],'abc')

    def test_schedule_unknown_finish_does_not_return_all_areas(self):
        document={"metadata":{},"objects":[{"id":"s1","type":"schedule_room","label":"Room 100 · OFFICE",
            "page":1,"properties":{"room_number":"100","area_ft2":108,"floor_finish":"F1"}}]}
        self.assertIsNone(answer_native("What is the area of rooms with wooden walls in the finish schedule?",document,self.root/'schedule.pdf',self.root))

    def test_selected_page_never_answers_another_storey(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'model.ifc').touch()
            source=root/'model_plan-04-4-korrus.pdf'
            model={"metadata":{"storeys":[{"guid":"s1","name":"1.korrus"},{"guid":"s4","name":"4.korrus"}]},
                   "objects":[{"id":"d1","guid":"g1","type":"IfcDoor","label":"Door1","page":1,"properties":{"storey_guid":"s1"}},
                              {"id":"d4","guid":"g4","type":"IfcDoor","label":"Door4","page":1,"properties":{"storey_guid":"s4"}}]}
            page={"metadata":{"requested_scope":"page"},"objects":[{"id":"v4","guid":"g4","type":"IfcDoor","label":"Door4","page":1,"bbox":[.1,.1,.2,.2],"properties":{}}]}
            with patch('server.native_qa._load',return_value=model):
                self.assertIsNone(answer_native("How many doors are on '1.korrus'?",page,source,root))
                result=answer_native("How many doors are there in the model?",page,source,root)
                self.assertEqual(result['value'],1)
                self.assertIn('selected floor',result['scope'])


if __name__=='__main__':
    unittest.main()
