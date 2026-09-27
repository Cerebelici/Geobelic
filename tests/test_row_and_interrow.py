"""
Unit tests for row extraction and quadrilateral interrow area derivation.
"""

import sys
import unittest
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.spatial.row_extractor import (
    estimate_row_angle,
    clip_line_to_tile,
    extract_rows_from_canopies,
)
from src.spatial.interrow import (
    derive_interrow_quadrilaterals,
    classify_interrow_cover,
)
from src.export.cvat_writer import CVATWriter, TileAnnotations


class RowAndInterrowTestCase(unittest.TestCase):
    def test_line_clipping_to_tile(self):
        """Test straight line clipping to [0, 2048] x [0, 2048] box."""
        rad = np.radians(45.0)
        norm_vec = np.array([-np.sin(rad), np.cos(rad)])
        prim_vec = np.array([np.cos(rad), np.sin(rad)])

        # Line passing through (1024, 1024): c = -1024*sin(45) + 1024*cos(45) = 0
        pts = clip_line_to_tile(c_val=0.0, normal_dir=norm_vec, primary_dir=prim_vec)
        self.assertEqual(len(pts), 2)
        self.assertEqual(pts[0], (0.0, 0.0))
        self.assertEqual(pts[1], (2048.0, 2048.0))

    def test_row_extraction_and_disruption(self):
        """Test clustering and gap detection (>= 5m / 200px gap triggers 'disrupted')."""
        # Row 1: Regular (spacing 50px = 1.25m)
        r1_pts = [(100.0, y) for y in range(200, 1000, 50)]
        # Row 2: Disrupted (contains a 250px gap from y=400 to y=650)
        r2_pts = [(200.0, y) for y in [200, 250, 300, 350, 400, 650, 700, 750, 800]]

        all_cents = r1_pts + r2_pts
        rows, targets, meta = extract_rows_from_canopies(all_cents, min_vines_per_row=3)

        self.assertEqual(len(rows), 2)
        # Check that one row is regular and one is disrupted
        structures = {r.row_structure for r in rows}
        self.assertIn("regular", structures)
        self.assertIn("disrupted", structures)
        self.assertGreaterEqual(len(targets), 1)

    def test_interrow_quadrilaterals(self):
        """Test that interrow areas between adjacent rows form clean straight quadrilaterals."""
        # 3 parallel vertical rows at x=200, x=350, x=500
        cents_r1 = [(200.0, y) for y in range(100, 1900, 60)]
        cents_r2 = [(350.0, y) for y in range(100, 1900, 60)]
        cents_r3 = [(500.0, y) for y in range(100, 1900, 60)]

        rows, targets, meta = extract_rows_from_canopies(cents_r1 + cents_r2 + cents_r3)
        self.assertEqual(len(rows), 3)

        margin_px = 12.0
        interrows = derive_interrow_quadrilaterals(
            rows_metadata=meta["rows_data"],
            normal_dir=meta["normal_dir"],
            primary_dir=meta["primary_dir"],
            vineyard_id="V01",
            margin_px=margin_px,
        )

        # 3 rows yield exactly 2 interrow corridors
        self.assertEqual(len(interrows), 2)

        for ir in interrows:
            self.assertEqual(ir.vineyard_id, "V01")
            self.assertIn(ir.interrow_cover, {"bare_soil", "vegetation", "mixed", "unassessable"})

            # Must be a quadrilateral (4 vertices)
            self.assertEqual(len(ir.points), 4)

            # Must be a strictly valid simple polygon
            poly = Polygon(ir.points)
            self.assertTrue(poly.is_valid)
            self.assertTrue(poly.exterior.is_simple)
            self.assertGreater(poly.area, 1000.0)

    def test_interrow_cover_classification(self):
        """Test Excess Green Index ground cover classifier."""
        # Clean green image (vegetation)
        green_img = np.zeros((100, 100, 3), dtype=np.uint8)
        green_img[:, :, 1] = 180  # high green
        pts = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]
        self.assertEqual(classify_interrow_cover(pts, green_img), "vegetation")

        # Clean brown/soil image (bare_soil: high red and blue, low green)
        soil_img = np.zeros((100, 100, 3), dtype=np.uint8)
        soil_img[:, :, 0] = 160  # Red
        soil_img[:, :, 1] = 100  # Green
        soil_img[:, :, 2] = 70   # Blue
        self.assertEqual(classify_interrow_cover(pts, soil_img), "bare_soil")


if __name__ == "__main__":
    unittest.main()

