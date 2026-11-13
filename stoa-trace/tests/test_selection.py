from pathlib import Path
import unittest
from server.selection import highlight_target, native_highlight, describe_highlights


class HighlightCommands(unittest.TestCase):
    def setUp(self):
        self.document = {'objects': [
            {'id': 'room-1', 'label': 'Stanza', 'type': 'room', 'page': 1, 'bbox': [.1, .1, .5, .5], 'properties': {'room_number': '5.11'}},
            {'id': 'door-1', 'label': 'Door', 'type': 'door', 'page': 1, 'bbox': [.1, .1, .2, .2], 'properties': {}},
            {'id': 'door-2', 'label': 'Door', 'type': 'door', 'page': 1, 'bbox': [.4, .4, .5, .5], 'properties': {}}], 'metadata': {}}

    def run_native(self, question):
        return native_highlight(question, self.document, Path('drawing.dxf'), Path('.'))

    def test_plain_highlight_reuses_native_counted_objects(self):
        result = describe_highlights(self.run_native('Can you highlight all the doors?'))
        self.assertEqual(result['highlighted_count'], 2)
        self.assertEqual({e['id'] for e in result['evidence']}, {'door-1', 'door-2'})

    def test_exact_room_identifier(self):
        result = describe_highlights(self.run_native('Please highlight room 5.11'))
        self.assertEqual(result['highlighted_count'], 1)
        self.assertEqual(result['evidence'][0]['id'], 'room-1')

    def test_unsupported_constraints_do_not_select_all(self):
        for question in ('Highlight all blue doors', 'Highlight "fire" doors', 'Highlight doors wider than 1m', 'Highlight room 5.11 with blue walls'):
            self.assertIsNone(self.run_native(question), question)

    def test_no_invented_projection_for_native_guid(self):
        result = describe_highlights({'evidence': [{'id': 'guid', 'label': 'Door'}], 'status': 'supported'})
        self.assertEqual(result['highlighted_count'], 0)
        self.assertEqual(result['matched_source_count'], 1)
        self.assertIn('unavailable', result['answer'])

    def test_questions_are_not_treated_as_commands(self):
        self.assertIsNone(highlight_target('How many doors are shown?'))


if __name__ == '__main__':
    unittest.main()
