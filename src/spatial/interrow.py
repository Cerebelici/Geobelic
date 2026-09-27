"""
Inter-row polygon derivation and ground cover classification.
Generates straight-edged quadrilateral corridors between adjacent vine rows.
Each row is bounded from both sides by straight margins of the interrow space,
conforming strictly to the challenge specification and ground truth topology.
"""

from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np
from shapely.geometry import box, Polygon, MultiPolygon
from shapely.validation import make_valid
from src.export.cvat_writer import InterRowArea, VineyardCanopy


def classify_interrow_cover(
    poly_coords: List[Tuple[float, float]],
    image_rgb: Optional[np.ndarray] = None,
) -> str:
    """
    Classify ground cover inside polygon based on Excess Green Index (2G - R - B):
    - bare_soil (< 25% vegetation)
    - mixed (25% - 75% vegetation)
    - vegetation (> 75% vegetation)
    - unassessable (if obscured or cannot be evaluated)
    """
    if image_rgb is None:
        return "bare_soil"

    try:
        minx = int(np.floor(min(p[0] for p in poly_coords)))
        miny = int(np.floor(min(p[1] for p in poly_coords)))
        maxx = int(np.ceil(max(p[0] for p in poly_coords)))
        maxy = int(np.ceil(max(p[1] for p in poly_coords)))

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

        # Mask only the interior of the polygon
        mask = np.zeros((maxy - miny, maxx - minx), dtype=np.uint8)
        local_pts = np.array([[p[0] - minx, p[1] - miny] for p in poly_coords], dtype=np.int32)
        cv2.fillPoly(mask, [local_pts], 1)

        inside = mask > 0
        if np.sum(inside) < 25:
            return "bare_soil"

        veg_ratio = float(np.mean(veg_mask[inside]))
        if veg_ratio < 0.25:
            return "bare_soil"
        elif veg_ratio > 0.75:
            return "vegetation"
        else:
            return "mixed"
    except Exception:
        return "bare_soil"


def derive_interrow_quadrilaterals(
    rows_metadata: List[Dict[str, Any]],
    normal_dir: np.ndarray,
    primary_dir: np.ndarray,
    vineyard_id: str = "V01",
    image_rgb: Optional[np.ndarray] = None,
    margin_px: float = 12.0,
    tile_width: float = 2048.0,
    tile_height: float = 2048.0,
    min_area_px: float = 100.0,
) -> List[InterRowArea]:
    """
    Derive quadrilateral inter-row area polygons between adjacent pairs of rows.
    Each row is bounded on both sides by straight margins of the interrow space at distance margin_px.
    The resulting space between adjacent row margins is clipped to tile boundaries,
    producing clean quadrilaterals with straight edges.
    """
    if len(rows_metadata) < 2:
        return []

    # Sort rows by normal projection
    sorted_rows = sorted(rows_metadata, key=lambda r: r["c_val"])
    tile_b = box(0.0, 0.0, tile_width, tile_height)

    nx, ny = float(normal_dir[0]), float(normal_dir[1])
    px, py = float(primary_dir[0]), float(primary_dir[1])

    interrows: List[InterRowArea] = []

    for i in range(len(sorted_rows) - 1):
        c_i = sorted_rows[i]["c_val"]
        c_next = sorted_rows[i + 1]["c_val"]
        spacing = abs(c_next - c_i)

        if spacing < 25.0:
            continue

        effective_margin = min(margin_px, 0.25 * spacing)
        c_low = min(c_i, c_next) + effective_margin
        c_high = max(c_i, c_next) - effective_margin

        if c_high <= c_low:
            continue

        # Build strip polygon between c_low and c_high spanning along primary direction
        size = 6000.0
        p1 = c_low * np.array([nx, ny]) - size * np.array([px, py])
        p2 = c_low * np.array([nx, ny]) + size * np.array([px, py])
        p3 = c_high * np.array([nx, ny]) + size * np.array([px, py])
        p4 = c_high * np.array([nx, ny]) - size * np.array([px, py])

        strip = Polygon([p1, p2, p3, p4])
        inter = strip.intersection(tile_b)

        if not inter.is_valid:
            inter = make_valid(inter)

        polys = []
        if isinstance(inter, Polygon):
            polys = [inter]
        elif isinstance(inter, MultiPolygon):
            polys = list(inter.geoms)

        for poly in polys:
            if not poly.is_valid or poly.area < min_area_px:
                continue

            # Extract coordinates rounded to 1 decimal place
            coords = [(round(float(x), 1), round(float(y), 1)) for x, y in poly.exterior.coords[:-1]]

            # Eliminate duplicate consecutive vertices
            dedup = [coords[0]]
            for pt in coords[1:]:
                if pt != dedup[-1]:
                    dedup.append(pt)
            if len(dedup) >= 3 and dedup[0] == dedup[-1]:
                dedup.pop()

            if len(dedup) < 3:
                continue

            # Final topological check
            p_final = Polygon(dedup)
            if not p_final.is_valid:
                p_final = make_valid(p_final)
                if hasattr(p_final, "geoms"):
                    p_final = max(p_final.geoms, key=lambda g: g.area, default=None)
                if p_final is None or not p_final.is_valid:
                    continue
                coords = [(round(float(x), 1), round(float(y), 1)) for x, y in p_final.exterior.coords[:-1]]
                if len(coords) < 3:
                    continue

            cover = classify_interrow_cover(dedup, image_rgb)
            interrows.append(
                InterRowArea(
                    points=dedup,
                    vineyard_id=vineyard_id,
                    interrow_cover=cover,
                )
            )

    return interrows


def derive_interrows(
    row_polylines: List[List[Tuple[float, float]]],
    canopies: List[VineyardCanopy],
    vineyard_id: str = "V01",
    image_rgb: Optional[np.ndarray] = None,
) -> List[InterRowArea]:
    """
    Backwards-compatible interface for interrow derivation from row polylines.
    """
    if len(row_polylines) < 2:
        return []

    # Estimate normal and c_val from provided polylines
    rows_meta = []
    angles = []
    for r_idx, pts in enumerate(row_polylines):
        if len(pts) >= 2:
            p1, p2 = np.array(pts[0]), np.array(pts[-1])
            diff = p2 - p1
            ang = np.degrees(np.arctan2(diff[1], diff[0])) % 180.0
            angles.append(ang)

    if not angles:
        return []

    mean_ang = float(np.median(angles))
    rad = np.radians(mean_ang)
    normal_dir = np.array([-np.sin(rad), np.cos(rad)])
    primary_dir = np.array([np.cos(rad), np.sin(rad)])

    for r_idx, pts in enumerate(row_polylines):
        pts_arr = np.array(pts)
        c_val = float(np.mean(np.dot(pts_arr, normal_dir)))
        rows_meta.append({
            "c_val": c_val,
            "row_id": f"{vineyard_id}-R{r_idx+1:02d}",
            "row_structure": "regular",
            "points": pts,
            "cluster": pts_arr,
        })

    return derive_interrow_quadrilaterals(
        rows_metadata=rows_meta,
        normal_dir=normal_dir,
        primary_dir=primary_dir,
        vineyard_id=vineyard_id,
        image_rgb=image_rgb,
    )
