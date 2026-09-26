import torch
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
from PIL import Image

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
from src.spatial.interrow import derive_interrows
from src.spatial.block_cluster import GlobalBlockClusterer
from src.spatial.row_stitcher import GlobalRowStitcher, LocalRowSegment


from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid


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
    def sanitize_polygon(raw_points: np.ndarray, min_area_px: float = 10.0) -> List[List[Tuple[float, float]]]:
        """
        Sanitizes a raw YOLO contour into 100% valid, non-self-intersecting closed polygons.
        - Fixes self-intersections (bowtie/hourglass artifacts) via make_valid
        - Decomposes MultiPolygons into separate simple polygons (eliminating bridge lines)
        - Simplifies vertices slightly to remove single-pixel spikes
        - Filters out degenerate shapes (< 3 vertices or area < min_area_px)
        """
        if len(raw_points) < 3:
            return []

        try:
            poly = Polygon(raw_points)
            if not poly.is_valid:
                poly = make_valid(poly)

            if isinstance(poly, Polygon):
                sub_polys = [poly]
            elif isinstance(poly, MultiPolygon):
                sub_polys = list(poly.geoms)
            else:
                return []

            valid_polys = []
            for sp in sub_polys:
                sp_clean = sp.simplify(0.5, preserve_topology=True)
                if sp_clean.is_valid and not sp_clean.is_empty and sp_clean.area >= min_area_px:
                    coords = [(round(float(x), 1), round(float(y), 1)) for x, y in sp_clean.exterior.coords[:-1]]
                    if len(coords) >= 3:
                        valid_polys.append(coords)
            return valid_polys
        except Exception:
            return []

    def process_batch(
        self,
        tile_paths: List[str],
        confidence: float = 0.28,
        imgsz: int = 1024,
        passages_geojson: str = "assets/02_route/passages.geojson",
        verbose: bool = True,
    ) -> Tuple[List[TileAnnotations], List[Tuple[float, float]]]:
        """
        Canopy-Focused Processing Pipeline:
        1. AI inference per tile (YOLO26 segmentation)
        2. Clean polygon sanitization (eliminates broken/bowtie polygons and cross-lines)
        3. Global block clustering (EPSG:32635) via 2.5m buffer & passage cuts
        4. Outputs TileAnnotations containing strictly clean canopies with persistent vineyard_id
        """
        tile_results = []
        tile_canopy_centroids: Dict[str, List[Tuple[float, float]]] = {}
        tile_parsed_indices: Dict[str, Optional[Tuple[int, int]]] = {}

        # -------------------------------------------------------------
        # Phase 1: Model inference & polygon sanitization
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
                    import cv2
                    dets = self.model.predict(tile_path, threshold=confidence)
                    if dets.mask is not None:
                        for m in dets.mask:
                            contours, _ = cv2.findContours(
                                m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                            )
                            for cnt in contours:
                                pts = cnt.reshape(-1, 2)
                                cleaned_polys = self.sanitize_polygon(pts, min_area_px=10.0)
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
                            cleaned_polys = self.sanitize_polygon(mask, min_area_px=10.0)
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
        # Phase 3: Assembly of Final TileAnnotations (Strictly Canopies)
        # -------------------------------------------------------------
        final_annotations: List[TileAnnotations] = []

        for t_data in tile_results:
            tile_name = t_data["tile_name"]
            coords = tile_parsed_indices.get(tile_name)
            tile_ann = TileAnnotations(image_name=tile_name, width=2048, height=2048)

            # Assign block IDs to sanitized canopies
            for pts, cent in zip(t_data["canopy_polys"], t_data["canopy_cents"]):
                if coords is not None:
                    r, c = coords
                    east, north = pixel_to_map(r, c, cent[0], cent[1])
                    v_id = clusterer.get_block_id_for_point(east, north)
                else:
                    v_id = "V01"
                tile_ann.canopies.append(VineyardCanopy(points=pts, vineyard_id=v_id))

            final_annotations.append(tile_ann)

        return final_annotations, []

    def process_tile(
        self,
        tile_path: str,
        vineyard_id: str = "V01",
        confidence: float = 0.28,
        imgsz: int = 1024,
    ) -> Tuple[TileAnnotations, List[Tuple[float, float]]]:
        """Process a single tile via the batch pipeline for consistent IDs."""
        anns, targets = self.process_batch([tile_path], confidence=confidence, imgsz=imgsz, verbose=False)
        return anns[0], targets

