import tempfile
import unittest
from pathlib import Path

from server.source_scope import unavailable_model_scope


class SourceScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / 'arbitrary_plan-02-upper.pdf'
        self.source.touch()
        self.document = {'metadata': {'semantic_svg': 'arbitrary_plan-02-upper.svg'},
                         'objects': [{'type': 'IfcDoor', 'guid': 'one-visible-door'}]}

    def test_model_counts_require_model_not_visible_subset(self):
        for question in ('How many doors are there in the model?',
                         'Wie viele Räume enthält das Modell „Any building“?'):
            result = unavailable_model_scope(question, self.document, self.source)
            self.assertEqual(result['status'], 'needs_input')
            self.assertIsNone(result['value'])

    def test_explicit_view_and_non_semantic_drawings_are_not_blocked(self):
        self.assertIsNone(unavailable_model_scope('How many doors are shown on this plan?', self.document, self.source))
        self.assertIsNone(unavailable_model_scope('How many rooms are in the building?', {'objects': []}, self.source))

    def test_supplied_native_model_remains_available(self):
        model = self.source.with_name('arbitrary.ifc')
        model.touch()
        self.assertIsNone(unavailable_model_scope('How many doors are in the model?', self.document, self.source))
        self.assertIsNone(unavailable_model_scope('Count model doors', self.document, model))
