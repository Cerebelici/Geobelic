"""
Robust row extraction and structure assessment module.
Uses nearest-neighbor directional histogram to accurately find row azimuth,
clusters canopies into physical rows, fits straight row polylines clipped to tile boundaries,
and identifies gaps >= 5m for disruption assessment.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from scipy.spatial import KDTree
from src.export.cvat_writer import VineRow
from src.spatial.grid import GSD


GAP_THRESHOLD_M = 5.0
GAP_THRESHOLD_PX = GAP_THRESHOLD_M / GSD  # 200 pixels at 0.025 m/px


def estimate_row_angle(points: np.ndarray) -> float:
    """
    Estimate dominant row azimuth (degrees, 0-180) using nearest-neighbor directional histogram.
    """
    if len(points) < 5:
        return 0.0

    tree = KDTree(points)
    angles = []
    # Query k nearest neighbors
    dists, indices = tree.query(points, k=min(6, len(points)))
    for i in range(len(points)):
        for d, j in zip(dists[i][1:], indices[i][1:]):
            # In-row vine spacing is typically 1.0 - 1.5m (40 - 60 px)
            if 25.0 <= d <= 85.0:
                diff = points[j] - points[i]
                ang = np.degrees(np.arctan2(diff[1], diff[0])) % 180.0
                angles.append(ang)

    if not angles:
        # Fallback to PCA if spacing differs
        mean = np.mean(points, axis=0)
        cov = np.cov(points - mean, rowvar=False)
        _, eigvecs = np.linalg.eigh(cov)
        v = eigvecs[:, 1]
        return float(np.degrees(np.arctan2(v[1], v[0])) % 180.0)

    # 1-degree bin histogram
    hist, bin_edges = np.histogram(angles, bins=180, range=(0, 180))
    # Smooth with simple moving window
    smoothed = np.convolve(hist, np.ones(5) / 5.0, mode="same")
    best_ang = bin_edges[np.argmax(smoothed)]
    return float(best_ang)


def get_line_tile_s_bounds(
    c_val: float,
    normal_dir: np.ndarray,
    primary_dir: np.ndarray,
    tile_width: float = 2048.0,
    tile_height: float = 2048.0,
) -> Optional[Tuple[float, float]]:
    """
    Compute analytical [s_min, s_max] parameter range along primary_dir
    where c_val * normal_dir + s * primary_dir lies within [0, tile_width] x [0, tile_height].
    """
    nx, ny = float(normal_dir[0]), float(normal_dir[1])
    px, py = float(primary_dir[0]), float(primary_dir[1])
    s_min = -1e9
    s_max = 1e9

    if abs(px) > 1e-7:
        b1 = (-c_val * nx) / px
        b2 = (tile_width - c_val * nx) / px
        s_min = max(s_min, min(b1, b2))
        s_max = min(s_max, max(b1, b2))
    elif c_val * nx < 0.0 or c_val * nx > tile_width:
        return None

    if abs(py) > 1e-7:
        b1 = (-c_val * ny) / py
        b2 = (tile_height - c_val * ny) / py
        s_min = max(s_min, min(b1, b2))
        s_max = min(s_max, max(b1, b2))
    elif c_val * ny < 0.0 or c_val * ny > tile_height:
        return None

    if s_min > s_max:
        return None
    return s_min, s_max


def clip_line_to_tile(
    c_val: float,
    normal_dir: np.ndarray,
    primary_dir: Optional[np.ndarray] = None,
    tile_width: float = 2048.0,
    tile_height: float = 2048.0,
) -> List[Tuple[float, float]]:
    """
    Clip straight line: -x*sin(theta) + y*cos(theta) = c_val
    to the tile bounding box [0, tile_width] x [0, tile_height].

    Returns 2 boundary intersection points [(x1, y1), (x2, y2)] rounded to 1 decimal.
    """
    if primary_dir is None:
        primary_dir = np.array([-normal_dir[1], normal_dir[0]])

    bounds = get_line_tile_s_bounds(c_val, normal_dir, primary_dir, tile_width, tile_height)
    if bounds is None:
        return []

    s_min, s_max = bounds
    p1 = c_val * normal_dir + s_min * primary_dir
    p2 = c_val * normal_dir + s_max * primary_dir

    p1_clamped = (
        round(float(np.clip(p1[0], 0.0, tile_width)), 1),
        round(float(np.clip(p1[1], 0.0, tile_height)), 1),
    )
    p2_clamped = (
        round(float(np.clip(p2[0], 0.0, tile_width)), 1),
        round(float(np.clip(p2[1], 0.0, tile_height)), 1),
    )

    if p1_clamped == p2_clamped:
        return []

    return [p1_clamped, p2_clamped]

def is_nodata_pixel(
    image_rgb: np.ndarray,
    x: float,
    y: float,
    dark_thresh: int = 25,
    patch_radius: int = 1,
) -> bool:
    """
    Check if a coordinate (x, y) falls inside a black nodata border area.
    Distinguishes real nodata borders (contiguous black pixels [0,0,0] from flight boundary)
    from isolated dark shadows (single-pixel deep shadows under vines or trellis).
    """
    h, w = image_rgb.shape[:2]
    ix = int(round(x))
    iy = int(round(y))
    c_ix = min(max(0, ix), w - 1)
    c_iy = min(max(0, iy), h - 1)

    # Fast single pixel check
    px = image_rgb[c_iy, c_ix]
    if int(px[0]) > dark_thresh or int(px[1]) > dark_thresh or int(px[2]) > dark_thresh:
        return False

    # Check local patch to confirm contiguous nodata region vs isolated shadow
    x0, x1 = max(0, c_ix - patch_radius), min(w, c_ix + patch_radius + 1)
    y0, y1 = max(0, c_iy - patch_radius), min(h, c_iy + patch_radius + 1)
    patch = image_rgb[y0:y1, x0:x1]

    # In true nodata regions, the vast majority of patch pixels are dark (<= dark_thresh)
    dark_fraction = float(np.mean((patch <= dark_thresh).all(axis=2)))
    return dark_fraction >= 0.4


def extract_rows_from_canopies(
    canopy_centroids: List[Tuple[float, float]],
    vineyard_id: str = "V01",
    row_prefix: str = "R",
    tile_width: int = 2048,
    tile_height: int = 2048,
    min_vines_per_row: int = 2,
    spacing_threshold_px: float = 45.0,
    return_metadata: bool = True,
    image_rgb: Optional[np.ndarray] = None,
    headland_margin_px: float = 60.0,
) -> Tuple[List[VineRow], List[Tuple[float, float]], Optional[Dict[str, Any]]]:
    """
    Extract vine row polylines from detected canopy centroids.
    Limits row polylines strictly to the physical vineyard planting:
    - Rows terminate at the first and last vine in that tile (+ headland margin ~60px / 1.5m).
    - Rows do not extend across roads, cleared land, or into black/nodata image borders.
    - Collinear row centerlines remain straight, aligned with dominant azimuth.

    Returns:
        (rows, inspection_targets, metadata)
    """
    if len(canopy_centroids) < min_vines_per_row:
        if return_metadata:
            return [], [], {"azimuth_deg": 0.0, "normal_dir": np.array([0.0, 1.0]), "primary_dir": np.array([1.0, 0.0]), "rows_data": []}
        return [], [], None

    pts = np.array(canopy_centroids, dtype=np.float32)

    # 1. Determine dominant row azimuth
    ang_deg = estimate_row_angle(pts)
    ang_rad = np.radians(ang_deg)

    # Unit vectors: primary_dir along row, normal_dir across rows
    primary_dir = np.array([np.cos(ang_rad), np.sin(ang_rad)], dtype=np.float32)
    normal_dir = np.array([-np.sin(ang_rad), np.cos(ang_rad)], dtype=np.float32)

    # 2. Project points onto normal direction
    proj_normal = np.dot(pts, normal_dir)

    # Sort points by normal projection
    sort_idx = np.argsort(proj_normal)
    sorted_pts = pts[sort_idx]
    sorted_proj = proj_normal[sort_idx]

    # Cluster into rows using spacing threshold (~45px, rows are ~100-120px apart)
    row_clusters = []
    current_cluster = [sorted_pts[0]]
    last_proj = sorted_proj[0]

    for i in range(1, len(sorted_pts)):
        if sorted_proj[i] - last_proj < spacing_threshold_px:
            current_cluster.append(sorted_pts[i])
        else:
            if len(current_cluster) >= min_vines_per_row:
                row_clusters.append(np.array(current_cluster))
            current_cluster = [sorted_pts[i]]
        last_proj = sorted_proj[i]

    if len(current_cluster) >= min_vines_per_row:
        row_clusters.append(np.array(current_cluster))

    # 3. For each cluster, fit polyline, check for gaps >= 5m, and create VineRow
    vine_rows: List[VineRow] = []
    inspection_targets: List[Tuple[float, float]] = []
    rows_data: List[Dict[str, Any]] = []

    for r_idx, cluster in enumerate(row_clusters, start=1):
        row_id = f"{vineyard_id}-{row_prefix}{r_idx:02d}"

        # Sort cluster along the row direction
        proj_along = np.dot(cluster, primary_dir)
        along_sort = np.argsort(proj_along)
        cluster_sorted = cluster[along_sort]
        proj_sorted = proj_along[along_sort]

        # Check for gaps between consecutive vines along row
        diffs = np.diff(cluster_sorted, axis=0)
        dists = np.linalg.norm(diffs, axis=1)

        has_disruption = False
        for d_idx, dist in enumerate(dists):
            if dist >= GAP_THRESHOLD_PX:
                has_disruption = True
                gap_center = 0.5 * (cluster_sorted[d_idx] + cluster_sorted[d_idx + 1])
                inspection_targets.append((round(float(gap_center[0]), 1), round(float(gap_center[1]), 1)))

        if len(cluster) < 2:
            row_structure = "unassessable"
        elif has_disruption:
            row_structure = "disrupted"
        else:
            row_structure = "regular"

        # Centreline normal coordinate
        c_mean = float(np.mean(np.dot(cluster, normal_dir)))

        # Bounds of the tile along primary_dir for this row
        tile_bounds = get_line_tile_s_bounds(
            c_val=c_mean,
            normal_dir=normal_dir,
            primary_dir=primary_dir,
            tile_width=float(tile_width),
            tile_height=float(tile_height),
        )

        # Minimum and maximum projection of vines along the row
        s_min_vine = float(proj_sorted[0])
        s_max_vine = float(proj_sorted[-1])

        if tile_bounds is not None:
            s_tile_min, s_tile_max = tile_bounds
            s_start_vine = min(max(s_min_vine, s_tile_min), s_tile_max)
            s_end_vine = min(max(s_max_vine, s_tile_min), s_tile_max)
        else:
            s_tile_min, s_tile_max = s_min_vine, s_max_vine
            s_start_vine, s_end_vine = s_min_vine, s_max_vine

        # Limit to outermost vines + headland margin (~60px / 1.5m), bounded by tile
        s_lo = max(s_start_vine - headland_margin_px, s_tile_min)
        s_hi = min(s_end_vine + headland_margin_px, s_tile_max)

        # If image_rgb is provided, ensure line does not extend into black/nodata borders
        if image_rgb is not None:
            def is_valid_s(s_val: float) -> bool:
                pt = c_mean * normal_dir + s_val * primary_dir
                return not is_nodata_pixel(image_rgb, pt[0], pt[1])

            # Trace outwards from first vine towards s_lo
            curr_s = s_start_vine
            step = 2.0
            stopped_early = False
            while curr_s - step >= s_lo:
                if not is_valid_s(curr_s - step):
                    s_lo = curr_s
                    stopped_early = True
                    break
                curr_s -= step
            if not stopped_early:
                if not is_valid_s(s_lo):
                    s_lo = curr_s

            # Trace outwards from last vine towards s_hi
            curr_s = s_end_vine
            stopped_early = False
            while curr_s + step <= s_hi:
                if not is_valid_s(curr_s + step):
                    s_hi = curr_s
                    stopped_early = True
                    break
                curr_s += step
            if not stopped_early:
                if not is_valid_s(s_hi):
                    s_hi = curr_s

        # Final safety bounds check against tile
        s_lo = max(s_lo, s_tile_min)
        s_hi = min(s_hi, s_tile_max)
        if s_lo > s_hi:
            s_lo, s_hi = s_start_vine, s_end_vine

        p_start = c_mean * normal_dir + s_lo * primary_dir
        p_end = c_mean * normal_dir + s_hi * primary_dir

        # Clamp endpoints strictly to [0, tile_width] x [0, tile_height]
        p_start = np.clip(p_start, [0.0, 0.0], [float(tile_width), float(tile_height)])
        p_end = np.clip(p_end, [0.0, 0.0], [float(tile_width), float(tile_height)])

        polyline_pts = [
            (round(float(p_start[0]), 1), round(float(p_start[1]), 1)),
            (round(float(p_end[0]), 1), round(float(p_end[1]), 1)),
        ]

        # Fallback to cluster endpoints if points collapsed
        if len(polyline_pts) < 2 or polyline_pts[0] == polyline_pts[1]:
            p_start_fb = cluster_sorted[0]
            p_end_fb = cluster_sorted[-1]
            p_start_fb = np.clip(p_start_fb, [0.0, 0.0], [float(tile_width), float(tile_height)])
            p_end_fb = np.clip(p_end_fb, [0.0, 0.0], [float(tile_width), float(tile_height)])
            polyline_pts = [
                (round(float(p_start_fb[0]), 1), round(float(p_start_fb[1]), 1)),
                (round(float(p_end_fb[0]), 1), round(float(p_end_fb[1]), 1)),
            ]

        # Recalculate true s_min and s_max from final polyline points
        final_s_0 = float(np.dot(np.array(polyline_pts[0]), primary_dir))
        final_s_1 = float(np.dot(np.array(polyline_pts[1]), primary_dir))
        actual_s_min = min(final_s_0, final_s_1)
        actual_s_max = max(final_s_0, final_s_1)

        v_row = VineRow(
            points=polyline_pts,
            vineyard_id=vineyard_id,
            row_id=row_id,
            row_structure=row_structure,
        )
        vine_rows.append(v_row)

        rows_data.append({
            "c_val": c_mean,
            "row_id": row_id,
            "row_structure": row_structure,
            "points": polyline_pts,
            "cluster": cluster,
            "vine_row": v_row,
            "s_min": actual_s_min,
            "s_max": actual_s_max,
        })

    meta = {
        "azimuth_deg": ang_deg,
        "normal_dir": normal_dir,
        "primary_dir": primary_dir,
        "rows_data": rows_data,
    }

    return vine_rows, inspection_targets, meta

