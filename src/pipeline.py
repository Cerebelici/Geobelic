"""
End-to-end processing pipeline:
Tile GeoTIFF -> AI Inference -> Spatial Post-Processing -> CVAT 1.1 XML & GeoJSON outputs.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
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


class VineyardPipeline:
    def __init__(self, model_weights_path: Optional[str] = None):
        self.model_weights = model_weights_path
        self.model = None
        if model_weights_path and Path(model_weights_path).exists():
            from ultralytics import YOLO
            self.model = YOLO(model_weights_path)

    def process_tile(
        self,
        tile_path: str,
        vineyard_id: str = "V01",
        confidence: float = 0.2,
        imgsz: int = 1024,
    ) -> Tuple[TileAnnotations, List[Tuple[float, float]]]:
        """
        Process a single tile:
        - Detect canopy polygons
        - Extract row polylines and gaps
        - Derive inter-row ground polygons
        - Return TileAnnotations and inspection targets in pixel coordinates
        """
        tile_name = Path(tile_path).name
        tile_ann = TileAnnotations(image_name=tile_name, width=2048, height=2048)
        inspection_targets: List[Tuple[float, float]] = []

        # Read image
        try:
            with Image.open(tile_path) as img:
                img_rgb = np.array(img.convert("RGB"))
        except Exception:
            img_rgb = None

        canopy_centroids = []

        if self.model is not None:
            results = self.model.predict(
                tile_path,
                conf=confidence,
                imgsz=imgsz,
                max_det=1500,
                device="mps",
                verbose=False,
            )[0]

            if results.masks is not None:
                for mask, cls in zip(results.masks.xy, results.boxes.cls):
                    cls_id = int(cls)
                    # Class 1 (pole) or Class 2 (trunk) or Class 0: vineyard canopy
                    if len(mask) >= 3:
                        pts = [(round(float(x), 1), round(float(y), 1)) for x, y in mask]
                        tile_ann.canopies.append(
                            VineyardCanopy(points=pts, vineyard_id=vineyard_id)
                        )
                        centroid = np.mean(mask, axis=0)
                        canopy_centroids.append((float(centroid[0]), float(centroid[1])))

            # Waste boxes (if present)
            if results.boxes is not None:
                for box, cls in zip(results.boxes.xyxy, results.boxes.cls):
                    # If model trained on waste class
                    pass

        # If canopies detected, extract rows and inter-rows
        if len(canopy_centroids) >= 3:
            rows, gaps = extract_rows_from_canopies(
                canopy_centroids=canopy_centroids,
                vineyard_id=vineyard_id,
            )
            tile_ann.rows = rows
            inspection_targets.extend(gaps)

            # Derive inter-row ground polygons
            row_lines = [r.points for r in rows]
            tile_ann.interrows = derive_interrows(
                row_polylines=row_lines,
                canopies=tile_ann.canopies,
                vineyard_id=vineyard_id,
                image_rgb=img_rgb,
            )

        return tile_ann, inspection_targets

