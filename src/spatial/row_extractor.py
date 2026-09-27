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
    nx, ny = float(normal_dir[0]), float(normal_dir[1])
    pts = []

    # Intersections with vertical boundaries x = 0 and x = tile_width
    if abs(ny) > 1e-5:
        y0 = c_val / ny
        if 0.0 <= y0 <= tile_height:
            pts.append((0.0, y0))
        y1 = (c_val - nx * tile_width) / ny
        if 0.0 <= y1 <= tile_height:
            pts.append((tile_width, y1))

    # Intersections with horizontal boundaries y = 0 and y = tile_height
    if abs(nx) > 1e-5:
        x0 = c_val / nx
        if 0.0 < x0 < tile_width:
            pts.append((x0, 0.0))
        x1 = (c_val - ny * tile_height) / nx
        if 0.0 < x1 < tile_width:
            pts.append((x1, tile_height))

    # Deduplicate points that are extremely close (< 0.2 px)
    unique_pts: List[Tuple[float, float]] = []
    for p in pts:
        if not any(np.hypot(p[0] - u[0], p[1] - u[1]) < 0.2 for u in unique_pts):
            unique_pts.append((round(float(p[0]), 1), round(float(p[1]), 1)))

    if len(unique_pts) == 2:
        if primary_dir is not None:
            px, py = float(primary_dir[0]), float(primary_dir[1])
            unique_pts.sort(key=lambda pt: pt[0] * px + pt[1] * py)
        return unique_pts
    elif len(unique_pts) > 2:
        # If clipped corner produces 3 points, take the two outermost points
        if primary_dir is not None:
            px, py = float(primary_dir[0]), float(primary_dir[1])
            unique_pts.sort(key=lambda pt: pt[0] * px + pt[1] * py)
            return [unique_pts[0], unique_pts[-1]]
        return unique_pts[:2]

    return []


def extract_rows_from_canopies(
    canopy_centroids: List[Tuple[float, float]],
    vineyard_id: str = "V01",
    row_prefix: str = "R",
    tile_width: int = 2048,
    tile_height: int = 2048,
    min_vines_per_row: int = 2,
    spacing_threshold_px: float = 45.0,
    return_metadata: bool = True,
) -> Tuple[List[VineRow], List[Tuple[float, float]], Optional[Dict[str, Any]]]:
    """
    Extract vine row polylines from detected canopy centroids.

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

        # Clip straight line to tile boundaries
        polyline_pts = clip_line_to_tile(
            c_val=c_mean,
            normal_dir=normal_dir,
            primary_dir=primary_dir,
            tile_width=float(tile_width),
            tile_height=float(tile_height),
        )

        # Fallback to cluster endpoints if clipping fails
        if len(polyline_pts) < 2:
            p_start = cluster_sorted[0]
            p_end = cluster_sorted[-1]
            polyline_pts = [
                (round(float(p_start[0]), 1), round(float(p_start[1]), 1)),
                (round(float(p_end[0]), 1), round(float(p_end[1]), 1)),
            ]

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
        })

    meta = {
        "azimuth_deg": ang_deg,
        "normal_dir": normal_dir,
        "primary_dir": primary_dir,
        "rows_data": rows_data,
    }

    return vine_rows, inspection_targets, meta

