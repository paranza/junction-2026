"""The schedule planner's deterministic executor and the model boundary (no network)."""
import unittest

from server import schedule_planner as sp

TABLES = [{
    "title": "DOOR SCHEDULE - TYPE", "page": 1,
    "header": ["Count", "Type Mark", "Type", "Width"],
    "rows": [
        {"id": "r0", "bbox": [0, 0, 1, 0.1], "cells": ["71", "U01", "UNIT DOOR", "3' - 0\""]},
        {"id": "r1", "bbox": [0, 0.1, 1, 0.2], "cells": ["4", "U3-LL", "LL-MARVIN ESSENTIAL SLIDING - 3RD FLOOR", "5' - 11 1/2\""]},
        {"id": "r2", "bbox": [0, 0.2, 1, 0.3], "cells": ["2", "U2-LR", "LR-MARVIN ESSENTIAL SLIDING - 2ND FLOOR", "5' - 11 1/2\""]},
        {"id": "r3", "bbox": [0, 0.3, 1, 0.4], "cells": ["118", "SS", "2-WIDE (TEMP ALL LOW) ESDH3066", "35 1/2\""]},
    ]}]


def plan(**kw):
    base = {"answerable": True, "table": 0, "filters": [], "aggregate": "count_rows", "value_columns": [],
            "multiplier_column": None, "explanation": ""}
    return {**base, **kw}


class Executor(unittest.TestCase):
    def test_filters_and_sum_of_count_column(self):
        r = sp.execute(plan(filters=[{"column": 2, "op": "contains", "values": ["MARVIN ESSENTIAL"]},
                                     {"column": 2, "op": "contains", "values": ["3RD FLOOR"]}],
                            aggregate="sum_column", value_columns=[0]), TABLES)
        self.assertEqual(r["value"], 4)
        self.assertEqual([x["id"] for x in r["rows"]], ["r1"])

    def test_sum_times_leading_number(self):
        r = sp.execute(plan(filters=[{"column": 1, "op": "equals", "values": ["SS"]}],
                            aggregate="sum_column_times_leading_number", value_columns=[0], multiplier_column=2), TABLES)
        self.assertEqual(r["value"], 236)

    def test_value_needs_exactly_one_row_and_feet_inches_match(self):
        r = sp.execute(plan(filters=[{"column": 3, "op": "equals", "values": ["3'-0\""]}], aggregate="value", value_columns=[1]), TABLES)
        self.assertEqual(r["value"], "Type Mark: U01")
        self.assertIsNone(sp.execute(plan(filters=[{"column": 2, "op": "contains", "values": ["MARVIN"]}],
                                          aggregate="value", value_columns=[1]), TABLES))

    def test_invalid_plans_are_refused(self):
        self.assertIsNone(sp.execute(plan(answerable=False), TABLES))
        self.assertIsNone(sp.execute(plan(table=3), TABLES))
        self.assertIsNone(sp.execute(plan(filters=[{"column": 9, "op": "equals", "values": ["X"]}]), TABLES))
        self.assertIsNone(sp.execute(plan(aggregate="sum_column", value_columns=[2]), TABLES))  # text column

    def test_answer_uses_the_model_only_for_the_plan_and_caches_it(self):
        calls = []

        def fake_request(content, system, schema, max_tokens):
            calls.append(content)
            return plan(filters=[{"column": 1, "op": "equals", "values": ["U01"]}], aggregate="sum_column", value_columns=[0])
        store = {}
        cache = (store.get, store.__setitem__)
        doc = {"metadata": {"schedule_tables": TABLES, "source_path": "x.pdf"}}
        first = sp.answer("How many unit doors?", doc, request=fake_request, cache=cache)
        second = sp.answer("How many unit doors?", doc, request=fake_request, cache=cache)
        self.assertEqual((first["value"], second["value"]), (71, 71))
        self.assertEqual(len(calls), 1)
        self.assertEqual(first["evidence"][0]["id"], "r0")
        self.assertEqual(first["method"], "model_planned_schedule_query")


if __name__ == "__main__":
    unittest.main()
