"""
Validation script for CVAT annotations XML.
Verifies:
1. 100% valid simple closed polygons (0 self-intersections).
2. Adherence to minimum area threshold (>= 300 px² / ~0.19 m²).
3. Avoidance of whole-row mergers (max area ceiling and distribution check).
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def validate_annotations(xml_path: str, min_area_px: float = 300.0, max_merged_area_px: float = 15000.0):
    xml_file = Path(xml_path)
    if not xml_file.exists():
        raise FileNotFoundError(f"Annotations file not found: {xml_file}")

    print("=" * 70)
    print(f"Validating Annotations XML: {xml_file.name}")
    print(f"File Path: {xml_file.resolve()}")
    print(f"File Size: {xml_file.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"Thresholds: min_area >= {min_area_px} px², max_merged_area <= {max_merged_area_px} px²")
    print("=" * 70)

    tree = ET.parse(xml_file)
    root = tree.getroot()

    images = root.findall("image")
    print(f"Total Images in XML: {len(images)}")

    total_polygons = 0
    invalid_geometry_count = 0
    self_intersection_count = 0
    below_min_area_count = 0
    merger_count = 0
    areas = []
    vertex_counts = []

    for img in images:
        img_name = img.get("name")
        polygons = img.findall("polygon")
        for poly_elem in polygons:
            total_polygons += 1
            pts_str = poly_elem.get("points")
            coords = []
            for pt in pts_str.split(";"):
                if "," in pt:
                    x_str, y_str = pt.split(",")
                    coords.append((float(x_str), float(y_str)))

            if len(coords) < 3:
                invalid_geometry_count += 1
                continue

            vertex_counts.append(len(coords))
            poly = Polygon(coords)

            if not poly.is_valid:
                invalid_geometry_count += 1
            if not poly.exterior.is_simple:
                self_intersection_count += 1

            area = poly.area
            areas.append(area)

            if area < min_area_px:
                below_min_area_count += 1

            if area > max_merged_area_px:
                merger_count += 1

    areas = np.array(areas) if areas else np.array([])
    vertex_counts = np.array(vertex_counts) if vertex_counts else np.array([])

    print("\n--- Validation Results ---")
    print(f"Total Polygons Evaluated:        {total_polygons}")
    print(f"Invalid Geometries:              {invalid_geometry_count}")
    print(f"Self-Intersections:              {self_intersection_count}")
    print(f"Polygons < {min_area_px:.0f} px²:           {below_min_area_count}")
    print(f"Suspected Whole-Row Mergers (> {max_merged_area_px:.0f} px²): {merger_count}")

    if len(areas) > 0:
        print("\n--- Polygon Statistics ---")
        print(f"Area Min:     {np.min(areas):.1f} px² ({np.min(areas) * 0.000625:.4f} m²)")
        print(f"Area 25%:    {np.percentile(areas, 25):.1f} px² ({np.percentile(areas, 25) * 0.000625:.4f} m²)")
        print(f"Area Median: {np.median(areas):.1f} px² ({np.median(areas) * 0.000625:.4f} m²)")
        print(f"Area Mean:   {np.mean(areas):.1f} px² ({np.mean(areas) * 0.000625:.4f} m²)")
        print(f"Area 75%:    {np.percentile(areas, 75):.1f} px² ({np.percentile(areas, 75) * 0.000625:.4f} m²)")
        print(f"Area Max:    {np.max(areas):.1f} px² ({np.max(areas) * 0.000625:.4f} m²)")
        print(f"Total Area:  {np.sum(areas):.1f} px² ({np.sum(areas) * 0.000625:.2f} m²)")
        print(f"Median Vertices per Polygon: {np.median(vertex_counts):.0f}")

    print("=" * 70)
    all_valid = (
        invalid_geometry_count == 0
        and self_intersection_count == 0
        and below_min_area_count == 0
        and merger_count == 0
    )
    if all_valid:
        print("✓ VALIDATION PASSED: 100% simple closed valid polygons, zero self-intersections, no whole-row mergers.")
    else:
        print("✗ VALIDATION FAILED: Found violations.")
    print("=" * 70)

    return all_valid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate CVAT annotations XML.")
    parser.add_argument("xml_path", type=str, nargs="?", default="annotations_part1.xml")
    parser.add_argument("--min-area", type=float, default=300.0)
    parser.add_argument("--max-merged-area", type=float, default=15000.0)
    args = parser.parse_args()

    success = validate_annotations(args.xml_path, min_area_px=args.min_area, max_merged_area_px=args.max_merged_area)
    sys.exit(0 if success else 1)
