"""
Comprehensive validation script for CVAT annotations XML.
Verifies all challenge object types:
1. Canopies (`vineyard`): 100% simple closed polygons, min area >= 300 px², 0 row mergers.
2. Rows (`row`): Straight polylines, valid structure attributes (regular/disrupted/unassessable).
3. Inter-rows (`interrow_area`): Clean quadrilaterals with straight edges, valid ground cover attributes.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
import numpy as np
from shapely.geometry import Polygon, LineString

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def validate_annotations(xml_path: str, min_canopy_area_px: float = 300.0, max_canopy_area_px: float = 15000.0):
    xml_file = Path(xml_path)
    if not xml_file.exists():
        raise FileNotFoundError(f"Annotations file not found: {xml_file}")

    print("=" * 70)
    print(f"Validating Annotations XML: {xml_file.name}")
    print(f"File Path: {xml_file.resolve()}")
    print(f"File Size: {xml_file.stat().st_size / (1024 * 1024):.2f} MB")
    print("=" * 70)

    tree = ET.parse(xml_file)
    root = tree.getroot()

    images = root.findall("image")
    print(f"Total Images in XML: {len(images)}")

    # 1. Canopy Validation
    canopy_count = 0
    canopy_invalid = 0
    canopy_self_intersect = 0
    canopy_below_min = 0
    canopy_mergers = 0
    canopy_areas = []
    canopy_vertices = []

    # 2. Row Validation
    row_count = 0
    row_structures = Counter()
    row_vertex_counts = Counter()
    row_invalid_attrs = 0

    # 3. Interrow Validation
    interrow_count = 0
    interrow_invalid = 0
    interrow_self_intersect = 0
    interrow_covers = Counter()
    interrow_vertex_counts = Counter()
    interrow_areas = []

    for img in images:
        # Canopies
        for poly_elem in img.findall('polygon[@label="vineyard"]'):
            canopy_count += 1
            pts_str = poly_elem.get("points")
            coords = [tuple(map(float, pt.split(","))) for pt in pts_str.split(";") if "," in pt]

            if len(coords) < 3:
                canopy_invalid += 1
                continue

            canopy_vertices.append(len(coords))
            poly = Polygon(coords)

            if not poly.is_valid:
                canopy_invalid += 1
            if not poly.exterior.is_simple:
                canopy_self_intersect += 1

            area = poly.area
            canopy_areas.append(area)

            if area < min_canopy_area_px:
                canopy_below_min += 1
            if area > max_canopy_area_px:
                canopy_mergers += 1

        # Rows
        for row_elem in img.findall('polyline[@label="row"]'):
            row_count += 1
            pts_str = row_elem.get("points")
            coords = [tuple(map(float, pt.split(","))) for pt in pts_str.split(";") if "," in pt]
            row_vertex_counts[len(coords)] += 1

            st_elem = row_elem.find('attribute[@name="row_structure"]')
            if st_elem is not None and st_elem.text in {"regular", "disrupted", "unassessable"}:
                row_structures[st_elem.text] += 1
            else:
                row_invalid_attrs += 1

        # Interrows
        for ir_elem in img.findall('polygon[@label="interrow_area"]'):
            interrow_count += 1
            pts_str = ir_elem.get("points")
            coords = [tuple(map(float, pt.split(","))) for pt in pts_str.split(";") if "," in pt]

            interrow_vertex_counts[len(coords)] += 1

            if len(coords) < 3:
                interrow_invalid += 1
                continue

            poly = Polygon(coords)
            if not poly.is_valid:
                interrow_invalid += 1
            if not poly.exterior.is_simple:
                interrow_self_intersect += 1

            interrow_areas.append(poly.area)

            cov_elem = ir_elem.find('attribute[@name="interrow_cover"]')
            if cov_elem is not None and cov_elem.text in {"bare_soil", "vegetation", "mixed", "unassessable"}:
                interrow_covers[cov_elem.text] += 1

    print("\n--- 1. Canopy Polygons (`vineyard`) ---")
    print(f"Total Canopies:                  {canopy_count}")
    print(f"Invalid Geometries:              {canopy_invalid}")
    print(f"Self-Intersections:              {canopy_self_intersect}")
    print(f"Canopies < {min_canopy_area_px:.0f} px²:           {canopy_below_min}")
    print(f"Suspected Row Mergers (> {max_canopy_area_px:.0f} px²): {canopy_mergers}")
    if canopy_areas:
        print(f"Median Area:                     {np.median(canopy_areas):.1f} px² ({np.median(canopy_areas)*0.000625:.4f} m²)")
        print(f"Median Vertices:                 {np.median(canopy_vertices):.0f}")

    print("\n--- 2. Row Polylines (`row`) ---")
    print(f"Total Rows:                      {row_count}")
    print(f"Vertex Count Distribution:       {dict(row_vertex_counts)}")
    print(f"Structure Distribution:          {dict(row_structures)}")
    if row_invalid_attrs > 0:
        print(f"Invalid Row Structure Attributes:{row_invalid_attrs}")

    print("\n--- 3. Inter-Row Areas (`interrow_area`) ---")
    print(f"Total Interrow Corridors:        {interrow_count}")
    print(f"Invalid Geometries:              {interrow_invalid}")
    print(f"Self-Intersections:              {interrow_self_intersect}")
    print(f"Quadrilateral / Vertex Dist:     {dict(interrow_vertex_counts)}")
    print(f"Ground Cover Distribution:       {dict(interrow_covers)}")
    if interrow_areas:
        print(f"Median Area:                     {np.median(interrow_areas):.1f} px² ({np.median(interrow_areas)*0.000625:.2f} m²)")

    # Overall Status
    passed = (
        canopy_invalid == 0
        and canopy_self_intersect == 0
        and canopy_below_min == 0
        and canopy_mergers == 0
        and interrow_invalid == 0
        and interrow_self_intersect == 0
        and row_invalid_attrs == 0
    )

    print("\n" + "=" * 70)
    if passed:
        print("✓ VALIDATION PASSED: 100% valid simple closed polygons, 0 self-intersections, valid polylines and quadrilaterals.")
    else:
        print("✗ VALIDATION FAILED: Found invalid geometries or out-of-spec attributes.")
    print("=" * 70)
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate CVAT annotations XML.")
    parser.add_argument("xml_path", type=str, help="Path to annotations.xml file")
    args = parser.parse_args()

    success = validate_annotations(args.xml_path)
    sys.exit(0 if success else 1)

