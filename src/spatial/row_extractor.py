"""
Robust row extraction and structure assessment module.
Uses nearest-neighbor directional histogram to accurately find row azimuth,
clusters canopies into physical rows, identifies gaps >= 5m, and fits row polylines.
"""

from typing import List, Tuple, Optional
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


def extract_rows_from_canopies(
    canopy_centroids: List[Tuple[float, float]],
    vineyard_id: str = "V01",
    row_prefix: str = "R",
    tile_width: int = 2048,
    tile_height: int = 2048,
) -> Tuple[List[VineRow], List[Tuple[float, float]]]:
    """
    Extract vine row polylines from detected canopy centroids.

    Returns:
        (rows, inspection_targets)
    """
    if len(canopy_centroids) < 3:
        return [], []

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

    # Cluster into rows using spacing threshold (~1.2m = 48 px)
    row_clusters = []
    current_cluster = [sorted_pts[0]]
    last_proj = sorted_proj[0]

    spacing_threshold_px = 50.0  # Rows are typically ~100px (2.5m) apart

    for i in range(1, len(sorted_pts)):
        if sorted_proj[i] - last_proj < spacing_threshold_px:
            current_cluster.append(sorted_pts[i])
        else:
            if len(current_cluster) >= 3:  # Valid row needs at least 3 vines
                row_clusters.append(np.array(current_cluster))
            current_cluster = [sorted_pts[i]]
        last_proj = sorted_proj[i]

    if len(current_cluster) >= 3:
        row_clusters.append(np.array(current_cluster))

    # 3. For each cluster, fit polyline, check for gaps >= 5m, and create VineRow
    vine_rows: List[VineRow] = []
    inspection_targets: List[Tuple[float, float]] = []

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
                inspection_targets.append((float(gap_center[0]), float(gap_center[1])))

        row_structure = "disrupted" if has_disruption else "regular"

        # Fit straight line polyline through endpoints
        p_start = cluster_sorted[0]
        p_end = cluster_sorted[-1]
        polyline_pts = [(round(float(p_start[0]), 1), round(float(p_start[1]), 1)),
                        (round(float(p_end[0]), 1), round(float(p_end[1]), 1))]

        vine_rows.append(
            VineRow(
                points=polyline_pts,
                vineyard_id=vineyard_id,
                row_id=row_id,
                row_structure=row_structure,
            )
        )

    return vine_rows, inspection_targets

