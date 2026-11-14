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
from server.normalize import to_english

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
