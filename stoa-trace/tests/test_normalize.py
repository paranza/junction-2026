"""Translated questions reach the native solvers in their English wording."""
import os
from pathlib import Path
import tempfile
import unittest

_temp = tempfile.TemporaryDirectory()
os.environ.setdefault('STOA_RUNTIME_DIR', str(Path(_temp.name) / 'runtime'))
os.environ.setdefault('STOA_DATA_ROOT', str(Path(_temp.name) / 'dataset'))
os.environ['STOA_ACCESS_TOKEN'] = ''

import pymupdf
from fastapi.testclient import TestClient

from server.app import app
from server.normalize import to_english, translation_preserves_constraints

# Labels are invented; only the sentence templates come from the question set.
CASES = [
    ('Kui suur on ruumi „TESTRUUM (1-1)“ netopõrandapind korrusel „9.korrus“ (m²)?',
     "What is the net floor area of the room 'TESTRUUM (1-1)' on '9.korrus', in m²?"),
    ("Hvad er nettoarealet af rummet 'Kontor (Rum nr. 999)' på '9. Sal' i m²?",
     "What is the net floor area of the room 'Kontor (Rum nr. 999)' on '9. Sal', in m²?"),
    ('Wie viele Türen enthält das Modell „Testhaus“?', "How many doors are there in the model 'Testhaus'?"),
    ('Quelle est la surface nette de la pièce 4.07 (« Séjour ») en m² ?',
     "What is the net floor area of room 4.07 ('Séjour') in m²?"),
    ('Wie gross ist die Nettofläche von Raum U2.01 («Keller») in m²?',
     "What is the net floor area of room U2.01 ('Keller') in m²?"),
    ("Qual è la superficie netta dell'appartamento F in m² (somma di tutti i locali, esclusi balconi, logge, "
     "terrazze e altri spazi esterni)?",
     'What is the net floor area of apartment F in m², summing all its rooms except balconies, loggias, terraces '
     'and other outdoor spaces?'),
    ('Kuinka monta ikkunaa pohjapiirustuksessa on?', 'How many windows are shown on this floor plan?'),
    ('Combien  de fenêtres sont dessinées sur ce plan ?', 'How many windows are drawn on this floor plan?'),
]


class Normalize(unittest.TestCase):
    def test_translated_templates_become_english(self):
        for question, english in CASES:
            with self.subTest(question=question):
                self.assertEqual(to_english(question), english)

    def test_labels_with_apostrophes_use_curly_quotes(self):
        expected = 'How many rooms labelled “Cage d\'escalier” are there on this floor?'
        self.assertEqual(to_english("Combien de pièces portant la désignation « Cage d'escalier » y a-t-il à cet étage ?"), expected)
        self.assertEqual(to_english("How many rooms labelled 'Cage d'escalier' are there on this floor?"), expected)

    def test_other_wording_is_unchanged(self):
        for question in ("How many rooms labelled 'Bad' are there on this floor?",
                         'Wie hoch ist das Gebäude?', 'Highlight all windows', ''):
            with self.subTest(question=question):
                self.assertEqual(to_english(question), question)

    def test_rewriting_is_idempotent(self):
        for question, _ in CASES:
            once = to_english(question)
            self.assertEqual(to_english(once), once)

    def test_quoted_label_whitespace_and_unicode_are_verbatim(self):
        label = "Cafe\u0301  Hall\tWest"
        source = f'Combien  de pièces portant la désignation « {label} » y a-t-il à cet étage ?'
        self.assertEqual(to_english(source), f"How many rooms labelled '{label}' are there on this floor?")
        label = "Cage  d'escalier\nNord"
        source = f'Combien de pièces portant la désignation « {label} » y a-t-il à cet étage ?'
        self.assertEqual(to_english(source), f'How many rooms labelled “{label}” are there on this floor?')


class TranslationSafety(unittest.TestCase):
    def assert_preserved(self, original, translated):
        self.assertTrue(translation_preserves_constraints(original, translated), (original, translated))

    def assert_rejected(self, original, translated):
        self.assertFalse(translation_preserves_constraints(original, translated), (original, translated))

    def test_known_multilingual_templates_preserve_constraints(self):
        for original, translated in CASES:
            with self.subTest(original=original):
                self.assert_preserved(original, translated)

    def test_labels_and_explicit_identifiers_cannot_change_or_disappear(self):
        source = 'Quelle est la surface de la pièce U2.01 « Salle  A » en m² ?'
        good = "What is the area of room U2.01 'Salle  A' in square metres?"
        self.assert_preserved(source, good)
        for translated in (good.replace('U2.01', 'U2.02'), good.replace('Salle  A', 'Salle A'),
                           good.replace("'Salle  A'", 'Salle A'), good.replace('U2.01 ', ''),
                           good.replace('U2.01', 'u2.01')):
            with self.subTest(translated=translated):
                self.assert_rejected(source, translated)
        self.assert_preserved('Fläche von Wohnung F in m²?', 'Area of apartment F in m²?')
        self.assert_rejected('Fläche von Wohnung F in m²?', 'Area of apartment A in m²?')
        self.assert_preserved('Raum ÄB1, 10 m²', 'Room ÄB1, 10 m²')
        self.assert_rejected('Raum ÄB1, 10 m²', 'Room AB1, 10 m²')
        self.assert_rejected('Room M2 area?', 'Room m2 area?')

    def test_numbers_and_equivalent_unit_spellings(self):
        self.assert_preserved('Quelle largeur dépasse 1,25 mètres ?', 'Which width is greater than 1.25 meters?')
        self.assert_preserved('Width 900 mm?', 'Width 900 millimeters?')
        self.assert_preserved('Area 10 m²?', 'Area 10 square metres?')
        self.assert_preserved('Area 10 mm²?', 'Area 10 square millimeters?')
        for original, translated in [('Width 900 mm?', 'Width 90 mm?'), ('Area 10 m²?', 'Area 10 m³?'),
                                     ('Width 900 mm?', 'Width 900 m?'), ('Width 900 mm?', 'Width mm?'),
                                     ('Width 900 mm?', 'Width 900 mm and 100 mm?'),
                                     ('Area 1,200 m²?', 'Area 1.2 m²?'),
                                     ('Width 1.200 mm?', 'Width 1.2 mm?')]:
            with self.subTest(original=original, translated=translated):
                self.assert_rejected(original, translated)

    def test_exclusions_only_and_negation_survive_translation(self):
        pairs = [('Nur Türen ohne Fenster', 'Only doors without windows'),
                 ('Solo porte senza finestre', 'Only doors excluding windows'),
                 ('Seulement les portes hors balcons', 'Only doors except balconies'),
                 ('Vain ovet, parvekkeet lukuun ottamatta', 'Only doors, not counting balconies'),
                 ('Ainult uksed, ilma akendeta', 'Only doors without windows'),
                 ('Kun døre uden vinduer', 'Only doors without windows'),
                 ('Ne comptez que les portes', 'Count only the doors'),
                 ('Nicht die Türen', 'Not the doors'),
                 ('Ne comptez pas les fenêtres', 'Do not count the windows')]
        for original, translated in pairs:
            with self.subTest(original=original):
                self.assert_preserved(original, translated)
        for original, translated in [('Nur Türen ohne Fenster', 'Doors without windows'),
                                     ('Nur Türen ohne Fenster', 'Only doors including windows'),
                                     ('Ne comptez que les portes', 'Count the doors'),
                                     ('Nicht die Türen', 'The doors'), ('The doors', 'Not the doors')]:
            with self.subTest(original=original):
                self.assert_rejected(original, translated)

    def test_comparison_boundaries_and_quantity_roles_cannot_change(self):
        self.assert_preserved('Mindestens 2 Fenster', 'At least 2 windows')
        self.assert_preserved('Au moins 2 fenêtres', 'Windows >= 2')
        self.assert_preserved('Nettofläche 10 m²', 'Net area 10 m²')
        self.assert_preserved('Bruttofläche 12 m²', 'Gross area 12 m²')
        self.assert_preserved('Alle Fenster', 'All windows')
        for original, translated in [('At least 2 windows', 'More than 2 windows'),
                                     ('At most 2 windows', 'At least 2 windows'),
                                     ('Exactly 2 windows', '2 windows'),
                                     ('Net area 10 m²', 'Gross area 10 m²'),
                                     ('Gross area 10 m²', 'Area 10 m²'), ('All windows', 'Windows')]:
            with self.subTest(original=original):
                self.assert_rejected(original, translated)

    def test_constraint_words_inside_labels_are_not_instructions(self):
        self.assert_preserved('Raum „Only  No 1“ in m²', "Room 'Only  No 1' in m²")
        self.assert_preserved("Pièce 'Cage d'escalier' en m²", 'Room “Cage d\'escalier” in m²')
        self.assert_rejected('Raum „Cafe\u0301“ in m²', "Room 'Café' in m²")

    def test_empty_or_non_string_translation_is_rejected(self):
        for original, translated in [('', ''), ('Windows?', ''), ('Windows?', None), (None, 'Windows?')]:
            with self.subTest(original=original, translated=translated):
                self.assert_rejected(original, translated)


class AskInterpretsTranslatedQuestions(unittest.TestCase):
    def test_answer_records_the_english_wording(self):
        pdf = pymupdf.open()
        pdf.new_page(width=600, height=400).insert_text((60, 80), 'Plan')
        data = pdf.tobytes()
        pdf.close()
        with TestClient(app) as client:
            upload = client.post('/api/upload', files=[('files', ('plan.pdf', data, 'application/pdf'))])
            self.assertEqual(upload.status_code, 200, upload.text)
            doc = upload.json()['documents'][0]
            reply = client.post('/api/ask', json={'document_id': doc['id'], 'question': 'Kuinka monta ikkunaa pohjapiirustuksessa on?',
                                                  'page': 1, 'scope': 'document', 'mode': 'native'})
            self.assertEqual(reply.status_code, 200, reply.text)
            body = reply.json()
            self.assertEqual(body['question'], 'Kuinka monta ikkunaa pohjapiirustuksessa on?')
            self.assertEqual(body['interpreted_question'], 'How many windows are shown on this floor plan?')


if __name__ == '__main__':
    unittest.main()
