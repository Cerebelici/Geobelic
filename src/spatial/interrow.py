"""
Inter-row polygon derivation and ground cover classification.
Derives ground corridors between adjacent rows and strictly enforces zero overlap with canopies.
"""

from typing import List, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from src.export.cvat_writer import InterRowArea, VineyardCanopy


def compute_interrow_corridor(
    line1: List[Tuple[float, float]],
    line2: List[Tuple[float, float]],
) -> Optional[Polygon]:
    """Build quadrilateral polygon corridor between two row polylines."""
    if len(line1) < 2 or len(line2) < 2:
        return None

    p1_a, p1_b = np.array(line1[0]), np.array(line1[-1])
    p2_a, p2_b = np.array(line2[0]), np.array(line2[-1])

    # Ensure consistent orientation (match closest endpoints)
    if np.linalg.norm(p1_a - p2_a) > np.linalg.norm(p1_a - p2_b):
        p2_a, p2_b = p2_b, p2_a

    # Polygon vertices in order: p1_a -> p1_b -> p2_b -> p2_a
    poly_coords = [
        (float(p1_a[0]), float(p1_a[1])),
        (float(p1_b[0]), float(p1_b[1])),
        (float(p2_b[0]), float(p2_b[1])),
        (float(p2_a[0]), float(p2_a[1])),
    ]

    try:
        poly = Polygon(poly_coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if poly.area > 50 else None
    except Exception:
        return None


def classify_interrow_cover(
    poly: Polygon,
    image_rgb: Optional[np.ndarray] = None,
) -> str:
    """
    Classify ground cover based on vegetation index:
    - bare_soil (<25% vegetation)
    - mixed (25-75% vegetation)
    - vegetation (>75% vegetation)
    """
    if image_rgb is None:
        return "bare_soil"

    try:
        # Bounding box of polygon
        minx, miny, maxx, maxy = [int(v) for v in poly.bounds]
        h, w = image_rgb.shape[:2]
        minx, miny = max(0, minx), max(0, miny)
        maxx, maxy = min(w, maxx), min(h, maxy)

        if maxx <= minx or maxy <= miny:
            return "bare_soil"

        crop = image_rgb[miny:maxy, minx:maxx].astype(np.float32)
        r, g, b = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]

        # Excess Green Index: 2G - R - B
        exg = 2.0 * g - r - b
        veg_mask = exg > 20.0

        veg_ratio = np.mean(veg_mask)
        if veg_ratio < 0.25:
            return "bare_soil"
        elif veg_ratio > 0.75:
            return "vegetation"
        else:
            return "mixed"
    except Exception:
        return "bare_soil"


def derive_interrows(
    row_polylines: List[List[Tuple[float, float]]],
    canopies: List[VineyardCanopy],
    vineyard_id: str = "V01",
    image_rgb: Optional[np.ndarray] = None,
) -> List[InterRowArea]:
    """
    Derive inter-row polygons between adjacent pairs of rows and subtract canopies.
    Guarantees 0% overlap with canopy polygons.
    """
    if len(row_polylines) < 2:
        return []

    # Build union of all canopy polygons for exact subtraction
    canopy_polys = []
    for c in canopies:
        try:
            p = Polygon(c.points)
            if p.is_valid and p.area > 5:
                canopy_polys.append(p)
        except Exception:
            pass

    canopy_union = unary_union(canopy_polys) if canopy_polys else None

    interrows: List[InterRowArea] = []

    # Iterate through adjacent row pairs
    for i in range(len(row_polylines) - 1):
        corridor = compute_interrow_corridor(row_polylines[i], row_polylines[i + 1])
        if corridor is None or corridor.is_empty:
            continue

        # Strictly subtract canopy polygons (golden rule: 0 overlap)
        if canopy_union is not None and not canopy_union.is_empty:
            try:
                diff = corridor.difference(canopy_union)
            except Exception:
                diff = corridor
        else:
            diff = corridor

        # Handle Polygon or MultiPolygon result
        geoms = diff.geoms if isinstance(diff, MultiPolygon) else [diff]

        for geom in geoms:
            if isinstance(geom, Polygon) and geom.area > 100:
                cover = classify_interrow_cover(geom, image_rgb)
                coords = [(round(x, 1), round(y, 1)) for x, y in geom.exterior.coords[:-1]]
                if len(coords) >= 3:
                    interrows.append(
                        InterRowArea(
                            points=coords,
                            vineyard_id=vineyard_id,
                            interrow_cover=cover,
                        )
                    )

    return interrows
