import torch
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid

from src.export.cvat_writer import (
    CVATWriter,
    TileAnnotations,
    VineRow,
    InterRowArea,
    VineyardCanopy,
    WasteBox,
)
from src.spatial.grid import parse_tile_indices, pixel_to_map, START_POINT
from src.spatial.row_extractor import extract_rows_from_canopies
from src.spatial.interrow import derive_interrows, derive_interrow_quadrilaterals
from src.spatial.block_cluster import GlobalBlockClusterer
from src.spatial.row_stitcher import GlobalRowStitcher, LocalRowSegment


def extract_polygons(geom) -> List[Polygon]:
    """Recursively extract all Polygon instances from Polygon, MultiPolygon, or GeometryCollection."""
    if isinstance(geom, Polygon):
        return [geom]
    elif hasattr(geom, "geoms"):
        res = []
        for g in geom.geoms:
            res.extend(extract_polygons(g))
        return res
    return []


def sanitize_and_format_polygon(
    poly: Polygon,
    min_area_px: float = 300.0,
    max_area_px: float = 15000.0,
    simplify_tol: float = 1.0,
) -> List[List[Tuple[float, float]]]:
    """
    Decimate with Douglas-Peucker, round to 1 decimal place, remove duplicate
    consecutive points, and strictly re-verify that the resulting geometry is:
    1. A valid simple closed polygon with 0 self-intersections.
    2. Strictly within [min_area_px, max_area_px] AFTER rounding.
    """
    if not poly.is_valid:
        poly = make_valid(poly)

    valid_coords_list = []
    for p in extract_polygons(poly):
        p_simp = p.simplify(simplify_tol, preserve_topology=True)
        if not p_simp.is_valid:
            p_simp = make_valid(p_simp)

        for sub_p in extract_polygons(p_simp):
            if sub_p.is_empty:
                continue
            # Extract exterior coordinates (dropping repeated endpoint)
            raw_coords = list(sub_p.exterior.coords)[:-1]
            if len(raw_coords) < 3:
                continue

            # Round coordinates to 1 decimal place as required by CVAT format
            rounded = [(round(float(x), 1), round(float(y), 1)) for x, y in raw_coords]

            # Eliminate consecutive duplicate vertices produced by rounding
            deduped = [rounded[0]]
            for pt in rounded[1:]:
                if pt != deduped[-1]:
                    deduped.append(pt)
            if len(deduped) > 1 and deduped[0] == deduped[-1]:
                deduped.pop()

            if len(deduped) < 3:
                continue

            # Re-verify topology and area of the actual rounded coordinates
            final_poly = Polygon(deduped)
            if not final_poly.is_valid:
                final_poly = make_valid(final_poly)

            for cand_poly in extract_polygons(final_poly):
                if (
                    cand_poly.is_valid
                    and not cand_poly.is_empty
                    and cand_poly.exterior.is_simple
                    and min_area_px <= cand_poly.area <= max_area_px
                ):
                    c_pts = [(round(float(x), 1), round(float(y), 1)) for x, y in cand_poly.exterior.coords[:-1]]
                    # Final deduplication
                    clean_c = [c_pts[0]]
                    for pt in c_pts[1:]:
                        if pt != clean_c[-1]:
                            clean_c.append(pt)
                    if len(clean_c) > 1 and clean_c[0] == clean_c[-1]:
                        clean_c.pop()
                    if len(clean_c) >= 3:
                        poly_eval = Polygon(clean_c)
                        if (
                            poly_eval.is_valid
                            and poly_eval.exterior.is_simple
                            and min_area_px <= poly_eval.area <= max_area_px
                        ):
                            valid_coords_list.append(clean_c)

    return valid_coords_list


def separate_canopy_polygon(
    pts_np: np.ndarray,
    min_dist_px: float = 40.0,
    min_area_px: float = 300.0,
    max_area_px: float = 15000.0,
    simplify_tol: float = 1.0,
) -> List[List[Tuple[float, float]]]:
    """
    Mentor Concepts Implementation:
    1. Morphological opening (3x3 ellipse) to sever flimsy single-pixel necks.
    2. Euclidean distance transform & marker-controlled watershed for elongated/touching canopies.
    3. Minimum area filtering (>= 300 px² / ~0.2 m²) and maximum area threshold (<= 15,000 px² / avoiding whole-row mergers).
    4. Topological sanitization (make_valid + GeometryCollection extraction) and
       Douglas-Peucker simplification (tol=1.0 px -> median 14 vertices matching GT).
    5. Post-rounding geometric re-validation ensuring 100% valid simple closed polygons.
    """
    if len(pts_np) < 3:
        return []

    min_x, min_y = pts_np.min(axis=0)
    max_x, max_y = pts_np.max(axis=0)
    w = max_x - min_x
    h = max_y - min_y
    diag = np.sqrt(w * w + h * h)
    aspect_ratio = max(w, h) / max(min(w, h), 1e-3)

    # If small or compact, sanitize directly without watershed
    if diag < 75 and aspect_ratio < 1.8:
        poly = Polygon(pts_np)
        return sanitize_and_format_polygon(
            poly, min_area_px=min_area_px, max_area_px=max_area_px, simplify_tol=simplify_tol
        )

    # Elongated / compound canopies: Morphological Opening & Distance-Transform Watershed
    pad = 4
    pw = int(np.ceil(w)) + 2 * pad
    ph = int(np.ceil(h)) + 2 * pad
    patch = np.zeros((ph, pw), dtype=np.uint8)
    local_pts = (pts_np - [min_x, min_y] + [pad, pad]).astype(np.int32)
    cv2.fillPoly(patch, [local_pts], 255)

    # 1. Morphological Opening (sever single-pixel weed bridges)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opened = cv2.morphologyEx(patch, cv2.MORPH_OPEN, kernel)

    # 2. Euclidean Distance Transform
    dist = cv2.distanceTransform(opened, cv2.DIST_L2, 5)

    footprint_size = int(min_dist_px)
    if footprint_size % 2 == 0:
        footprint_size += 1
    local_max = (dist == maximum_filter(dist, size=footprint_size)) & (dist > 5.0)
    peak_y, peak_x = np.where(local_max)

    # Single peak: extract contour from opened mask
    if len(peak_x) <= 1:
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_polys = []
        for cnt in contours:
            if len(cnt) >= 3:
                cnt_pts = cnt.reshape(-1, 2) + [min_x - pad, min_y - pad]
                valid_polys.extend(
                    sanitize_and_format_polygon(
                        Polygon(cnt_pts),
                        min_area_px=min_area_px,
                        max_area_px=max_area_px,
                        simplify_tol=simplify_tol,
                    )
                )
        return valid_polys

    # Multiple peaks: Marker-controlled watershed
    markers = np.zeros_like(opened, dtype=np.int32)
    for m_id, (px, py) in enumerate(zip(peak_x, peak_y), start=1):
        cv2.circle(markers, (px, py), 2, m_id, -1)

    color_patch = cv2.cvtColor(opened, cv2.COLOR_GRAY2BGR)
    cv2.watershed(color_patch, markers)

    valid_polys = []
    for m_id in range(1, len(peak_x) + 1):
        sub_mask = ((markers == m_id) & (opened > 0)).astype(np.uint8) * 255
        if sub_mask.sum() == 0:
            continue
        contours, _ = cv2.findContours(sub_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if len(cnt) >= 3:
                cnt_pts = cnt.reshape(-1, 2) + [min_x - pad, min_y - pad]
                valid_polys.extend(
                    sanitize_and_format_polygon(
                        Polygon(cnt_pts),
                        min_area_px=min_area_px,
                        max_area_px=max_area_px,
                        simplify_tol=simplify_tol,
                    )
                )
    return valid_polys


class VineyardPipeline:
    def __init__(self, model_weights_path: Optional[str] = None):
        self.model_weights = model_weights_path
        self.model = None
        self.model_type = "yolo"
        self.device = self._select_device()
        if model_weights_path and Path(model_weights_path).exists():
            p = str(model_weights_path)
            if p.endswith(".pth") or "rfdetr" in p.lower():
                from rfdetr import RFDETRSegLarge
                self.model_type = "rfdetr"
                self.model = RFDETRSegLarge.from_checkpoint(p)
            else:
                from ultralytics import YOLO
                self.model_type = "yolo"
                self.model = YOLO(p)

    @staticmethod
    def _select_device() -> str:
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        return "cpu"

    @staticmethod
    def sanitize_polygon(
        raw_points: np.ndarray, min_area_px: float = 300.0, max_area_px: float = 15000.0
    ) -> List[List[Tuple[float, float]]]:
        """Wrapper around separate_canopy_polygon for backward compatibility."""
        return separate_canopy_polygon(raw_points, min_area_px=min_area_px, max_area_px=max_area_px)

    def process_batch(
        self,
        tile_paths: List[str],
        confidence: float = 0.28,
        imgsz: int = 2048,
        min_plant_dist_px: float = 40.0,
        min_area_px: float = 300.0,
        max_area_px: float = 15000.0,
        extract_rows: bool = True,
        extract_interrows: bool = True,
        margin_px: float = 12.0,
        passages_geojson: str = "assets/02_route/passages.geojson",
        verbose: bool = True,
    ) -> Tuple[List[TileAnnotations], List[Tuple[float, float]]]:
        """
        Complete Vineyard Pipeline:
        1. High-resolution AI inference per tile (YOLO26-Seg native 2048x2048)
        2. Morphological opening & distance-transform watershed separation
        3. Clean polygon sanitization & Douglas-Peucker decimation (median 12-14 vertices)
        4. Global block clustering (EPSG:32635) via 2.5m buffer & passage cuts
        5. Straight-line row extraction & gap disruption assessment (regular/disrupted)
        6. Clean quadrilateral inter-row area derivation bounded by row margins
        """
        tile_results = []
        tile_canopy_centroids: Dict[str, List[Tuple[float, float]]] = {}
        tile_parsed_indices: Dict[str, Optional[Tuple[int, int]]] = {}

        # -------------------------------------------------------------
        # Phase 1: Model inference & polygon separation
        # -------------------------------------------------------------
        for idx, tile_path in enumerate(tile_paths, start=1):
            tile_name = Path(tile_path).name
            try:
                r, c = parse_tile_indices(tile_name)
                tile_parsed_indices[tile_name] = (r, c)
            except Exception:
                tile_parsed_indices[tile_name] = None

            canopy_polys: List[List[Tuple[float, float]]] = []
            canopy_cents: List[Tuple[float, float]] = []

            if self.model is not None:
                if self.model_type == "rfdetr":
                    dets = self.model.predict(tile_path, threshold=confidence)
                    if dets.mask is not None:
                        for m in dets.mask:
                            contours, _ = cv2.findContours(
                                m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                            )
                            for cnt in contours:
                                pts = cnt.reshape(-1, 2)
                                cleaned_polys = separate_canopy_polygon(
                                    pts,
                                    min_dist_px=min_plant_dist_px,
                                    min_area_px=min_area_px,
                                    max_area_px=max_area_px,
                                    simplify_tol=1.0,
                                )
                                for poly_coords in cleaned_polys:
                                    canopy_polys.append(poly_coords)
                                    c_poly = Polygon(poly_coords)
                                    canopy_cents.append((float(c_poly.centroid.x), float(c_poly.centroid.y)))
                else:
                    results = self.model.predict(
                        tile_path,
                        conf=confidence,
                        imgsz=imgsz,
                        max_det=1500,
                        device=self.device,
                        verbose=False,
                    )[0]

                    if results.masks is not None:
                        for mask in results.masks.xy:
                            cleaned_polys = separate_canopy_polygon(
                                mask,
                                min_dist_px=min_plant_dist_px,
                                min_area_px=min_area_px,
                                max_area_px=max_area_px,
                                simplify_tol=1.0,
                            )
                            for poly_coords in cleaned_polys:
                                canopy_polys.append(poly_coords)
                                c_poly = Polygon(poly_coords)
                                canopy_cents.append((float(c_poly.centroid.x), float(c_poly.centroid.y)))

            tile_canopy_centroids[tile_name] = canopy_cents
            tile_results.append({
                "tile_name": tile_name,
                "tile_path": tile_path,
                "canopy_polys": canopy_polys,
                "canopy_cents": canopy_cents,
            })

            if verbose:
                print(f"[{idx}/{len(tile_paths)}] Processed {tile_name}: {len(canopy_polys)} valid canopies")

        # -------------------------------------------------------------
        # Phase 2: Global Block Clustering (EPSG:32635)
        # -------------------------------------------------------------
        clusterer = GlobalBlockClusterer(passages_geojson=passages_geojson)
        has_georef = any(idx is not None for idx in tile_parsed_indices.values())

        if has_georef:
            clusterer.cluster_blocks(tile_canopy_centroids, buffer_distance_m=2.5)

        # -------------------------------------------------------------
        # Phase 3: Assembly of TileAnnotations (Canopies, Rows, Interrows)
        # -------------------------------------------------------------
        final_annotations: List[TileAnnotations] = []
        all_targets: List[Tuple[float, float]] = []

        # Intermediate row storage: tile_name -> block_id -> (v_rows, meta)
        tile_block_rows: Dict[str, Dict[str, Tuple[List[VineRow], Dict[str, Any]]]] = defaultdict(dict)
        block_row_segments: Dict[str, List[LocalRowSegment]] = defaultdict(list)

        for t_data in tile_results:
            tile_name = t_data["tile_name"]
            coords = tile_parsed_indices.get(tile_name)
            tile_ann = TileAnnotations(image_name=tile_name, width=2048, height=2048)

            # Assign block IDs to canopies and group centroids per block
            block_canopy_map: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
            for pts, cent in zip(t_data["canopy_polys"], t_data["canopy_cents"]):
                if coords is not None:
                    r, c = coords
                    east, north = pixel_to_map(r, c, cent[0], cent[1])
                    v_id = clusterer.get_block_id_for_point(east, north)
                else:
                    v_id = "V01"
                tile_ann.canopies.append(VineyardCanopy(points=pts, vineyard_id=v_id))
                block_canopy_map[v_id].append(cent)

            # Extract straight row lines per block
            if extract_rows:
                for b_id, b_cents in block_canopy_map.items():
                    if len(b_cents) >= 2:
                        v_rows, targets, meta = extract_rows_from_canopies(
                            canopy_centroids=b_cents,
                            vineyard_id=b_id,
                            tile_width=2048,
                            tile_height=2048,
                            min_vines_per_row=2,
                            return_metadata=True,
                        )
                        tile_block_rows[tile_name][b_id] = (v_rows, meta)
                        all_targets.extend(targets)

                        if coords is not None:
                            r, c = coords
                            for vr in v_rows:
                                g_pts = [pixel_to_map(r, c, px, py) for px, py in vr.points]
                                block_row_segments[b_id].append(
                                    LocalRowSegment(
                                        tile_name=tile_name,
                                        local_points=vr.points,
                                        global_points=g_pts,
                                        block_id=b_id,
                                        row_structure=vr.row_structure,
                                    )
                                )

            final_annotations.append(tile_ann)

        # Cross-tile row stitching if georeferenced and multiple tiles
        if has_georef and len(tile_paths) > 1 and extract_rows:
            stitcher = GlobalRowStitcher()
            stitched_ids_map = {}
            for b_id, segs in block_row_segments.items():
                if segs:
                    updated_segs = stitcher.stitch_block_rows(b_id, segs)
                    for s in updated_segs:
                        if s.assigned_row_id and s.local_points:
                            key = (s.tile_name, b_id, s.local_points[0])
                            stitched_ids_map[key] = s.assigned_row_id

            # Apply stitched IDs
            for tile_ann in final_annotations:
                t_name = tile_ann.image_name
                for b_id, (v_rows, meta) in tile_block_rows.get(t_name, {}).items():
                    for vr in v_rows:
                        if vr.points:
                            key = (t_name, b_id, vr.points[0])
                            if key in stitched_ids_map:
                                vr.row_id = stitched_ids_map[key]

        # Add rows and derive quadrilateral inter-row areas
        for idx, tile_ann in enumerate(final_annotations):
            t_name = tile_ann.image_name
            t_path = tile_results[idx]["tile_path"]

            # Load image for ground cover classification if needed
            im_rgb = None
            if extract_interrows and Path(t_path).exists():
                try:
                    im_rgb = np.array(Image.open(t_path).convert("RGB"))
                except Exception:
                    im_rgb = None

            for b_id, (v_rows, meta) in tile_block_rows.get(t_name, {}).items():
                tile_ann.rows.extend(v_rows)

                if extract_interrows and meta and len(meta.get("rows_data", [])) >= 2:
                    ir_quads = derive_interrow_quadrilaterals(
                        rows_metadata=meta["rows_data"],
                        normal_dir=meta["normal_dir"],
                        primary_dir=meta["primary_dir"],
                        vineyard_id=b_id,
                        image_rgb=im_rgb,
                        margin_px=margin_px,
                        tile_width=2048.0,
                        tile_height=2048.0,
                    )
                    tile_ann.interrows.extend(ir_quads)

        return final_annotations, all_targets

    def process_tile(
        self,
        tile_path: str,
        vineyard_id: str = "V01",
        confidence: float = 0.28,
        imgsz: int = 2048,
        min_area_px: float = 300.0,
        max_area_px: float = 15000.0,
        extract_rows: bool = True,
        extract_interrows: bool = True,
        margin_px: float = 12.0,
    ) -> Tuple[TileAnnotations, List[Tuple[float, float]]]:
        """Process a single tile via the batch pipeline for consistent IDs."""
        anns, targets = self.process_batch(
            [tile_path],
            confidence=confidence,
            imgsz=imgsz,
            min_area_px=min_area_px,
            max_area_px=max_area_px,
            extract_rows=extract_rows,
            extract_interrows=extract_interrows,
            margin_px=margin_px,
            verbose=False,
        )
        return anns[0], targets

