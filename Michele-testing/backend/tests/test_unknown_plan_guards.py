"""Unknown drawings must not turn missing semantics or scale into measured zeros.

No trained model, GPU or hosted service is used by these checks.
"""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from stoa import llm, pipeline, questions, takeoff


def room(identifier="r1", **extra):
    return {"id": identifier, "number": "1.01", "name": None, "category": "unlabelled",
            "area_m2": None, "area_geom_m2": None, "area_px": 100,
            "area_source": "set the scale to measure", "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "centroid": [5, 5], "unit": "A", "outdoor": False, "shaft": False, **extra}


def unknown():
    return {"source": "raster", "style": "geometry", "scale": {"m_per_px": None, "method": "not calibrated"},
            "rooms": [room()], "units": [{"id": "A", "area_m2": None}],
            "objects": [{"id": "o1", "type": "opening"}], "words": [], "storeys": 1, "warnings": []}


class UnknownDrawingGuards(unittest.TestCase):
    def test_unclassified_openings_are_not_zero_doors_or_windows(self):
        for question in ("How many doors are drawn?", "How many windows are drawn?", "How many kitchens?",
                         "How many apartments?", "How many floors (storeys)?"):
            answer = questions.answer(question, unknown())
            self.assertIsNone(answer["value"], question)
            self.assertEqual(answer["status"], "insufficient_evidence")

    def test_supported_category_can_still_have_a_real_zero(self):
        facts = {"source": "dxf", "rooms": [], "objects": [], "units": []}
        self.assertEqual(questions.answer("How many doors are drawn?", facts)["value"], 0)

    def test_missing_room_area_does_not_become_zero_or_partial_total(self):
        facts = unknown()
        facts["rooms"].append(room("r2", number="1.02", area_m2=12.5, area_source="printed label (PDF text)"))
        for question in ("What is the total net floor area in m²?", "What is the area of apartment A in m²?",
                         "What is the net area of room 1.01 in m²?"):
            self.assertIsNone(questions.answer(question, facts)["value"])

    def test_legacy_assumed_scale_does_not_revalidate_old_area(self):
        facts = unknown()
        facts["scale"] = {"m_per_px": .02, "method": "assumed 1:200 sheet at 150 dpi"}
        facts["rooms"][0].update(area_m2=25, area_source="segmented geometry x calibrated scale")
        self.assertIsNone(questions.answer("What is the total net floor area in m²?", facts)["value"])
        self.assertTrue(all(v is None for v in takeoff.compute(facts)["totals"].values()))

    def test_printed_area_can_be_read_without_assuming_pixel_scale(self):
        facts = unknown()
        facts["rooms"][0].update(area_m2=12.5, area_source="printed label (PDF text)")
        self.assertEqual(questions.answer("What is the net area of room 1.01 in m²?", facts)["value"], 12.5)

    def test_user_calibration_enables_geometry_area_but_not_object_classification(self):
        facts = pipeline.apply_scale(unknown(), .1, "calibrated by user (1 m)")
        self.assertEqual(facts["summary"]["net_area_m2"], 1)
        self.assertEqual(questions.answer("What is the total net floor area in m²?", facts)["value"], 1)
        self.assertIsNone(questions.answer("How many doors are drawn?", facts)["value"])
        for invalid in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                pipeline.apply_scale(unknown(), invalid, "calibrated by user")

    def test_scale_requires_three_consistent_printed_area_matches(self):
        good = [{"area_label": 10, "pixels": 1000}, {"area_label": 20, "pixels": 2000},
                {"area_label": 30, "pixels": 3000}]
        self.assertAlmostEqual(pipeline._printed_scale(good)[0], .1)
        self.assertIsNone(pipeline._printed_scale(good[:2])[0])
        bad = [*good[:2], {"area_label": 300, "pixels": 3000}]
        self.assertIsNone(pipeline._printed_scale(bad)[0])

    def test_raster_without_scale_keeps_printed_values_and_withholds_geometry(self):
        rooms = [{"pixels": 1000, "area_label": 12.5}, {"pixels": 2000, "area_label": None}]
        pipeline._raster_areas(rooms, None, "pdf")
        self.assertEqual(rooms[0]["area_m2"], 12.5)
        self.assertIsNone(rooms[0]["area_geom_m2"])
        self.assertIsNone(rooms[1]["area_m2"])
        self.assertIsNone(pipeline._area_sum(rooms))
        self.assertIsNone(pipeline._area_sum([]))

    def test_unknown_scale_serializes_for_fallback_and_takeoff(self):
        facts = pipeline.summarize(unknown())
        self.assertIn("scale: unknown", llm.compact(facts))
        self.assertIsNone(facts["summary"]["net_area_m2"])
        result = takeoff.compute(facts)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertTrue(all(value is None for value in result["totals"].values()))

    def test_empty_analysis_does_not_claim_a_measured_scale_or_zero_counts(self):
        import numpy as np
        facts = pipeline._empty_facts(np.zeros((5, 5), np.uint8), "raster", "No model available")
        self.assertIsNone(facts["scale"]["m_per_px"])
        self.assertIsNone(facts["summary"]["net_area_m2"])
        self.assertIsNone(questions.answer("How many doors are drawn?", facts)["value"])

    def test_api_returns_explanation_instead_of_none_as_a_number(self):
        from fastapi.testclient import TestClient
        spec = importlib.util.spec_from_file_location("prototype_guard_api", BACKEND / "app.py")
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        with patch.object(api, "_load", return_value=unknown()), patch.object(llm, "ask", side_effect=AssertionError("No hosted calls")):
            response = TestClient(api.app).post("/api/analysis/test/ask", json={"question": "How many doors are drawn?"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["value"])
        self.assertIn("Not answered", response.json()["answer"])

    def test_non_swiss_pdf_does_not_enter_swiss_model_path(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new-plan.pdf"
            pdf = pymupdf.open()
            pdf.new_page(width=600, height=400)
            pdf.save(path)
            pdf.close()
            facts = unknown()
            with patch.object(pipeline, "analyze_geometry", return_value=facts) as geometry, \
                    patch.object(pipeline, "analyze_raster", side_effect=AssertionError("Unknown PDF must not use Swiss model")):
                _, result = pipeline.analyze_file(str(path))
            geometry.assert_called_once()
            self.assertTrue(any("first PDF page" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
