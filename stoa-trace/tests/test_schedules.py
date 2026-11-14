"""Ruled schedule extraction and code-based counts on synthetic PDFs (no dataset needed)."""
import tempfile
import unittest
from pathlib import Path

import fitz

from server.schedules import answer_count, find_tables, split_header


def ruled_pdf(path, title, rows, col_w=70, row_h=14, x0=50, y0=80):
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_text((x0, y0 - 6), title, fontsize=8)
    cols = len(rows[0])
    for i in range(len(rows) + 1):
        page.draw_line((x0, y0 + i * row_h), (x0 + cols * col_w, y0 + i * row_h))
    for j in range(cols + 1):
        page.draw_line((x0 + j * col_w, y0), (x0 + j * col_w, y0 + len(rows) * row_h))
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            if text:
                page.insert_text((x0 + j * col_w + 3, y0 + i * row_h + 10), text, fontsize=7)
    doc.save(path)


def tables_of(path):
    page = fitz.open(path)[0]
    out = []
    for t in find_tables(page):
        header, body = split_header(t["rows"], t.get("header_above"))
        out.append({"title": t["title"], "header": header, "touches_below": t["touches_below"],
                    "rows": [{"cells": [c["text"] for c in r]} for r in body]})
    return out


class Schedules(unittest.TestCase):
    def test_header_words_without_digits_and_counts_by_code(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            path = Path(folder) / "s.pdf"
            ruled_pdf(path, "DOOR SCHEDULE - TYPE", [
                ["Count", "Type Mark", "Type", "Width"],
                ["71", "U01", "UNIT DOOR", "3' - 0\""],
                ["15", "U22", "CHAINLINK GATE", "3' - 0\""],
                ["10", "U44", "SLIDING", "6' - 0\""]])
            tables = tables_of(path)
            table = next(t for t in tables if "SCHEDULE" in t["title"])
            self.assertEqual(table["header"], ["Count", "Type Mark", "Type", "Width"])
            self.assertEqual(len(table["rows"]), 3)
            ask = lambda q: (answer_count(q, tables) or {}).get("value")
            self.assertEqual(ask("How many chain-link gates (type U22) are scheduled?"), 15)
            self.assertEqual(ask("How many doors (types U01 and U44) are scheduled?"), 81)
            self.assertEqual(ask("How many items in total are counted in the door type schedule?"), 96)
            self.assertIsNone(ask("How many doors of type U99 are scheduled?"))                 # unknown code
            self.assertIsNone(ask("How many doors of type U01 are scheduled on the 3rd floor?"))  # scope words

    def test_room_schedule_whose_rows_start_with_words(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            path = Path(folder) / "r.pdf"
            ruled_pdf(path, "ROOM SCHEDULE", [["Level", "Name", "Area"], ["BASEMENT", "BOAT HOUSE", "371 SF"],
                                              ["MAIN", "KITCHEN", "120 SF"], ["MAIN", "DOOR STORE", "10 SF"]])
            table = next(t for t in tables_of(path) if "SCHEDULE" in t["title"])
            self.assertEqual(table["header"], ["Level", "Name", "Area"])
            self.assertEqual([r["cells"][1] for r in table["rows"]], ["BOAT HOUSE", "KITCHEN", "DOOR STORE"])


if __name__ == "__main__":
    unittest.main()
