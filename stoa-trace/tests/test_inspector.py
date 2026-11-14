"""Takeoff and code checks on a synthetic metric plan (no dataset needed)."""
import unittest

from server.inspector import classify, inspect

W = H = 1000.0  # page points; 1 pt = 0.01 m below


def rect(x0, y0, x1, y1):
    return [[x0 / W, y0 / H], [x1 / W, y0 / H], [x1 / W, y1 / H], [x0 / W, y1 / H]]


def room(rid, label, x0, y0, x1, y1, **props):
    area = (x1 - x0) * (y1 - y0) * 0.0001
    return {"id": rid, "type": "room", "label": label, "polygon": rect(x0, y0, x1, y1),
            "bbox": [x0 / W, y0 / H, x1 / W, y1 / H],
            "properties": {"net_area_m2": area, "geometry_area_m2": area, "room_number": rid, **props}}


def plan(door_to_bath=True):
    objects = [
        room("1", "Treppenhaus", 0, 0, 300, 400),          # stairwell 3 x 4 m
        room("2", "Wohnen/Essen", 300, 0, 800, 400),       # living 5 x 4 m
        room("3", "Bagno", 800, 0, 1000, 200),             # bathroom 2 x 2 m
        room("4", "Zimmer", 800, 200, 1000, 400),          # isolated room: no door
        {"id": "d1", "type": "door", "polygon": rect(295, 150, 305, 240), "bbox": [0.295, 0.15, 0.305, 0.24], "properties": {}},
        {"id": "w1", "type": "window", "polygon": rect(400, 0, 700, 5), "bbox": [0.4, 0, 0.7, 0.005], "properties": {}},
        {"id": "t1", "type": "toilet", "bbox": [0.93, 0.02, 0.99, 0.09], "properties": {}},
    ]
    if door_to_bath:
        objects.append({"id": "d2", "type": "door", "polygon": rect(795, 60, 805, 140), "bbox": [0.795, 0.06, 0.805, 0.14], "properties": {}})
    return {"format": "pdf", "pages": [{"page": 1, "width": W, "height": H}], "objects": objects}


class Inspector(unittest.TestCase):
    def test_room_labels_map_across_languages(self):
        self.assertEqual(classify("Cage d'escalier")[0], "stair")
        self.assertEqual(classify("Soggiorno/pranzo")[0], "living")
        self.assertEqual(classify("KPH")[0], "bathroom")
        self.assertEqual(classify("TUALETTRUUM (58-3)")[0], "wc")
        self.assertEqual(classify("MAGAMISTUBA (59-2)")[0], "bedroom")
        self.assertEqual(classify("xyz"), (None, None))

    def test_takeoff_quantities_come_from_the_drawing(self):
        result = inspect(plan())
        self.assertAlmostEqual(result["scale_m_per_pt"], 0.01, places=4)
        boq = {line["key"]: line for line in result["boq"]}
        self.assertEqual(boq["door"]["quantity"], 2)
        self.assertAlmostEqual(boq["window"]["quantity"], 3.0, places=1)
        self.assertEqual(boq["toilet"]["evidence"], ["t1"])
        self.assertAlmostEqual(result["totals"]["total_eur"], sum(l["total_eur"] for l in result["boq"]), places=2)

    def test_daylight_turning_circle_and_egress(self):
        result = inspect(plan())
        checks = {(c["check"], c["room"]): c for c in result["checks"]}
        living = checks[("daylight", "2")]
        self.assertAlmostEqual(living["value"], 3.0 * 1.4 / 20.0, places=2)  # 3 m window, 1.4 m glass, 20 m²
        self.assertEqual(living["status"], "pass")
        self.assertEqual(checks[("daylight", "4")]["status"], "fail")      # no window
        bath = checks[("turning_circle", "3")]
        # 2 x 2 m with a WC in one corner leaves about a 1.4 m free circle: not wheelchair accessible
        self.assertTrue(1.2 < bath["value"] < 2.0)
        self.assertEqual(bath["status"], "fail")
        egress = next(c for c in result["checks"] if c["check"] == "egress")
        self.assertEqual(egress["room"], "3")                                # bathroom is furthest from the stair
        self.assertTrue(4 < egress["value"] < 9)
        self.assertEqual(egress["status"], "incomplete")                     # room 4 has no door
        self.assertTrue(egress["path"])

    def test_unconnected_rooms_are_not_reported_as_reachable(self):
        result = inspect(plan(door_to_bath=False))
        egress = next(c for c in result["checks"] if c["check"] == "egress")
        self.assertEqual(egress["room"], "2")

    def test_whole_ifc_model_skips_plan_geometry(self):
        doc = plan()
        doc["format"] = "ifc"
        result = inspect(doc)
        self.assertIsNone(result["scale_m_per_pt"])
        self.assertFalse([c for c in result["checks"] if c["check"] == "egress"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
